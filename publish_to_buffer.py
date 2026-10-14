import os
import re
import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from google import genai

BUFFER_API_URL = "https://api.buffer.com"
BUFFER_API_KEY = os.environ.get("BUFFER_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.6-flash"
SITE_BASE_URL = "https://sho-support.github.io/ai-trend-blog"
HISTORY_FILE = Path("article_history.json")
BUFFER_HISTORY_FILE = Path("buffer_post_history.json")
ARTICLE_DIR = Path("articles")
TARGET_X_HANDLE = "AITrendBlogJP"

if not BUFFER_API_KEY:
    raise RuntimeError("BUFFER_API_KEY が設定されていません。")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY が設定されていません。")

client = genai.Client(api_key=GEMINI_API_KEY)


def buffer_graphql(query):
    response = requests.post(
        BUFFER_API_URL,
        headers={
            "Authorization": f"Bearer {BUFFER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"query": query},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(f"Buffer GraphQL error: {payload['errors']}")
    return payload.get("data", {})


def get_x_channel_id():
    account_data = buffer_graphql(
        """
        query {
          account {
            organizations {
              id
              name
            }
          }
        }
        """
    )
    organizations = account_data.get("account", {}).get("organizations", [])
    if not organizations:
        raise RuntimeError("Buffer organization が見つかりません。")

    candidates = []
    for organization in organizations:
        org_id = organization.get("id", "")
        if not re.fullmatch(r"[0-9a-fA-F]{24}", org_id):
            continue

        channel_data = buffer_graphql(
            f"""
            query {{
              channels(input: {{ organizationId: \"{org_id}\" }}) {{
                id
                name
                displayName
                service
                externalLink
                isDisconnected
                isLocked
              }}
            }}
            """
        )

        for channel in channel_data.get("channels", []):
            if channel.get("service") != "twitter":
                continue
            if channel.get("isDisconnected") or channel.get("isLocked"):
                continue
            candidates.append(channel)

    if not candidates:
        raise RuntimeError("接続済みのXチャンネルが見つかりません。")

    target_lower = TARGET_X_HANDLE.lower()
    for channel in candidates:
        values = [
            str(channel.get("name", "")),
            str(channel.get("displayName", "")),
            str(channel.get("externalLink", "")),
        ]
        if any(target_lower in value.lower() for value in values):
            print("Xチャンネル検出:", channel)
            return channel["id"]

    if len(candidates) == 1:
        print("Xチャンネルを1件検出:", candidates[0])
        return candidates[0]["id"]

    raise RuntimeError(
        "Xチャンネルを特定できません: "
        + json.dumps(candidates, ensure_ascii=False)
    )


def load_json_list(path):
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except Exception:
        return []


def article_text(filename):
    path = ARTICLE_DIR / filename
    if not path.exists():
        return ""

    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


def create_x_copy(item):
    filename = item["filename"]
    title = item.get("title", "")
    source_name = item.get("source_name", "")
    article_url = f"{SITE_BASE_URL}/articles/{filename}"
    body = article_text(filename)[:5000]

    prompt = f"""
あなたは日本向けAIニュースメディア「AI Trend Blog」のX運用担当です。
以下の記事からX投稿本文を1件だけ作ってください。

目的:
・リンククリックにつなげる
・一般のAI関心層にも気になると思わせる
・煽りすぎない
・記事にない事実を追加しない

ルール:
・日本語
・URLを除いて220文字以内を目安
・1行目で一番気になるポイントを伝える
・要点は最大2〜3個
・絵文字は0〜2個
・ハッシュタグは原則なし
・誇大表現禁止
・最後は「詳しくはこちら👇」
・URLは本文に含めない
・投稿本文だけを返す

媒体: {source_name}
タイトル: {title}
記事本文:
{body}
"""

    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    text = (response.text or "").strip().replace("```", "").strip()
    text = re.sub(r"https?://\S+", "", text).strip()

    if not text:
        text = title
    if len(text) > 235:
        text = text[:234].rstrip() + "…"

    return f"{text}\n{article_url}"


def create_buffer_post(channel_id, text):
    gql_text = json.dumps(text, ensure_ascii=False)

    data = buffer_graphql(
        f"""
        mutation CreatePost {{
          createPost(input: {{
            text: {gql_text}
            channelId: \"{channel_id}\"
            schedulingType: automatic
            mode: addToQueue
            aiAssisted: true
          }}) {{
            ... on PostActionSuccess {{
              post {{
                id
                text
                dueAt
                status
              }}
            }}
            ... on MutationError {{
              message
            }}
          }}
        }}
        """
    )

    result = data.get("createPost", {})
    if result.get("message"):
        raise RuntimeError(f"Buffer投稿作成失敗: {result['message']}")

    post = result.get("post")
    if not post:
        raise RuntimeError(f"Buffer投稿作成結果が不明です: {result}")

    return post


def main():
    history = load_json_list(HISTORY_FILE)
    posted = load_json_list(BUFFER_HISTORY_FILE)
    posted_files = {item.get("filename") for item in posted}

    pending = [
        item
        for item in history
        if item.get("filename") and item.get("filename") not in posted_files
    ]

    if not pending:
        print("Bufferへ送る新規記事はありません。")
        return

    latest = pending[-1]
    filename = latest["filename"]
    print("Buffer投稿対象:", filename)

    channel_id = get_x_channel_id()
    text = create_x_copy(latest)
    print("X投稿文:")
    print(text)

    post = create_buffer_post(channel_id, text)

    posted.append(
        {
            "filename": filename,
            "buffer_post_id": post.get("id"),
            "due_at": post.get("dueAt"),
        }
    )

    BUFFER_HISTORY_FILE.write_text(
        json.dumps(posted, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Buffer予約完了:", post)


if __name__ == "__main__":
    main()
