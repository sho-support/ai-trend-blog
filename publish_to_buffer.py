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

MODEL_NAME = "gemini-3.8-flash"
FALLBACK_MODEL_NAMES = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
]

SITE_BASE_URL = "https://sho-support.github.io/ai-trend-blog"
HISTORY_FILE = Path("article_history.json")
BUFFER_HISTORY_FILE = Path("buffer_post_history.json")
ARTICLE_DIR = Path("articles")
TARGET_X_HANDLE = "AITrendBlogJP"

# Xの280文字制限に安全マージンを持たせる。
MAX_X_WEIGHT = 270
URL_WEIGHT = 23

if not BUFFER_API_KEY:
    raise RuntimeError("BUFFER_API_KEY が設定されていません。")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY が設定されていません。")

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_content_with_fallback(contents, purpose="Gemini生成"):
    model_names = [
        MODEL_NAME,
        *FALLBACK_MODEL_NAMES,
    ]

    last_error = None

    for model_name in model_names:
        try:
            print(f"{purpose}: {model_name} を使用")
            return client.models.generate_content(
                model=model_name,
                contents=contents,
            )
        except Exception as e:
            last_error = e
            print(
                f"{purpose}エラー [{model_name}]:",
                e,
            )

    raise RuntimeError(
        f"{purpose}失敗: 全モデルで生成できませんでした: {last_error}"
    )


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
        raise RuntimeError(
            f"Buffer GraphQL error: {payload['errors']}"
        )

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

    organizations = (
        account_data
        .get("account", {})
        .get("organizations", [])
    )

    if not organizations:
        raise RuntimeError(
            "Buffer organization が見つかりません。"
        )

    candidates = []

    for organization in organizations:
        org_id = organization.get("id", "")

        if not re.fullmatch(
            r"[0-9a-fA-F]{24}",
            org_id,
        ):
            continue

        channel_data = buffer_graphql(
            f"""
            query {{
              channels(
                input: {{
                  organizationId: "{org_id}"
                }}
              ) {{
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

        for channel in channel_data.get(
            "channels",
            [],
        ):
            if channel.get("service") != "twitter":
                continue

            if (
                channel.get("isDisconnected")
                or channel.get("isLocked")
            ):
                continue

            candidates.append(channel)

    if not candidates:
        raise RuntimeError(
            "接続済みのXチャンネルが見つかりません。"
        )

    target_lower = TARGET_X_HANDLE.lower()

    for channel in candidates:
        values = [
            str(channel.get("name", "")),
            str(channel.get("displayName", "")),
            str(channel.get("externalLink", "")),
        ]

        if any(
            target_lower in value.lower()
            for value in values
        ):
            print(
                "Xチャンネル検出:",
                channel,
            )
            return channel["id"]

    if len(candidates) == 1:
        print(
            "Xチャンネルを1件検出:",
            candidates[0],
        )
        return candidates[0]["id"]

    raise RuntimeError(
        "Xチャンネルを特定できません: "
        + json.dumps(
            candidates,
            ensure_ascii=False,
        )
    )


def load_json_list(path):
    if not path.exists():
        return []

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        return (
            value
            if isinstance(value, list)
            else []
        )

    except Exception:
        return []


def article_text(filename):
    path = ARTICLE_DIR / filename

    if not path.exists():
        return ""

    soup = BeautifulSoup(
        path.read_text(
            encoding="utf-8"
        ),
        "html.parser",
    )

    for tag in soup(
        [
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
        ]
    ):
        tag.decompose()

    return re.sub(
        r"\s+",
        " ",
        soup.get_text(
            " ",
            strip=True,
        ),
    ).strip()


def x_char_weight(ch):
    code = ord(ch)

    if (
        0x0000 <= code <= 0x10FF
        or 0x2000 <= code <= 0x200D
        or 0x2010 <= code <= 0x201F
        or 0x2032 <= code <= 0x2037
    ):
        return 1

    return 2


def x_weighted_length(text):
    total = 0
    last_end = 0

    for match in re.finditer(
        r"https?://\S+",
        text,
    ):
        plain = text[
            last_end:match.start()
        ]

        total += sum(
            x_char_weight(ch)
            for ch in plain
        )

        total += URL_WEIGHT
        last_end = match.end()

    tail = text[last_end:]

    total += sum(
        x_char_weight(ch)
        for ch in tail
    )

    return total


def truncate_to_weight(
    text,
    max_weight,
):
    text = text.strip()

    if x_weighted_length(text) <= max_weight:
        return text

    result = []
    current_weight = 0

    for ch in text:
        weight = x_char_weight(ch)

        if (
            current_weight
            + weight
            + 2
            > max_weight
        ):
            break

        result.append(ch)
        current_weight += weight

    return "".join(result).rstrip() + "…"


def clean_generated_text(text):
    text = (text or "").strip()
    text = text.replace("```", "").strip()

    text = re.sub(
        r"https?://\S+",
        "",
        text,
    ).strip()

    text = re.sub(
        r"(?im)^投稿[12]\s*[:：]?\s*",
        "",
        text,
    ).strip()

    return text


def create_thread_copy(item):
    filename = item["filename"]
    title = item.get("title", "")
    source_name = item.get(
        "source_name",
        "",
    )

    article_url = (
        f"{SITE_BASE_URL}/articles/"
        f"{filename}"
    )

    body = article_text(
        filename
    )[:6000]

    hook_prompt = f"""
あなたは日本向けAIニュースメディア「AI Trend Blog」のX運用担当です。

以下の記事から、Xスレッドの1投目だけを作ってください。

【目的】
・タイムライン上でスクロールを止めてもらう
・「続きが気になる」と思わせる
・リンクは入れず、まず投稿そのものを読ませる
・煽りすぎず信頼感を保つ

【クリックされやすくするルール】
・最初の1行で「何が変わるのか」「なぜ注目か」を伝える
・単なる「○○を発表」ではなく、ユーザーにとっての意味を先に出す
・数字、比較、意外性が記事内にある場合だけ優先して使う
・2〜3行程度
・要点は最大2つ
・日本語
・本文は80〜120文字程度
・絵文字は0〜1個
・ハッシュタグなし
・URLなし
・「詳しくはこちら」などの誘導文なし
・記事にない事実は禁止
・過剰な断定や煽りは禁止
・投稿本文だけ返す

媒体:
{source_name}

タイトル:
{title}

記事本文:
{body}
"""

    cta_prompt = f"""
あなたは日本向けAIニュースメディア「AI Trend Blog」のX運用担当です。

以下の記事から、Xスレッドの2投目だけを作ってください。

【目的】
・1投目を読んだ人に記事リンクをクリックしてもらう

【ルール】
・日本語
・35〜70文字程度
・記事を読むメリットを具体的に1つ伝える
・「日本で使えるのか」「料金」「向いている人」「注意点」など、
  記事本文に実際に書かれている要素だけを使う
・1投目の内容を繰り返さない
・絵文字は0〜1個
・ハッシュタグなし
・URLは書かない
・最後は自然な誘導文にする
・記事にない事実は禁止
・投稿本文だけ返す

媒体:
{source_name}

タイトル:
{title}

記事本文:
{body}
"""

    hook_response = generate_content_with_fallback(
        hook_prompt,
        purpose="Xスレッド1投目生成",
    )

    cta_response = generate_content_with_fallback(
        cta_prompt,
        purpose="Xスレッド2投目生成",
    )

    first_post = clean_generated_text(
        hook_response.text
    )

    second_body = clean_generated_text(
        cta_response.text
    )

    if not first_post:
        first_post = title

    if not second_body:
        second_body = (
            "記事ではポイントと注意点を"
            "わかりやすく整理しています。"
        )

    # 1投目はリンクなし。安全側に240相当まで。
    first_post = truncate_to_weight(
        first_post,
        240,
    )

    # 2投目はリンク付き。
    suffix = (
        "\n\n記事はこちら👇\n"
        + article_url
    )

    allowed_second_body = (
        MAX_X_WEIGHT
        - x_weighted_length(suffix)
    )

    second_body = truncate_to_weight(
        second_body,
        allowed_second_body,
    )

    second_post = (
        second_body
        + suffix
    )

    if (
        x_weighted_length(first_post)
        > MAX_X_WEIGHT
    ):
        raise RuntimeError(
            "Xスレッド1投目が文字数上限を超えています。"
        )

    if (
        x_weighted_length(second_post)
        > MAX_X_WEIGHT
    ):
        raise RuntimeError(
            "Xスレッド2投目が文字数上限を超えています。"
        )

    print(
        "Xスレッド1投目 重み付き文字数:",
        x_weighted_length(first_post),
    )

    print(
        "Xスレッド2投目 重み付き文字数:",
        x_weighted_length(second_post),
    )

    return (
        first_post,
        second_post,
    )


def create_buffer_thread(
    channel_id,
    first_post,
    second_post,
):
    first_json = json.dumps(
        first_post,
        ensure_ascii=False,
    )

    second_json = json.dumps(
        second_post,
        ensure_ascii=False,
    )

    data = buffer_graphql(
        f"""
        mutation CreateThreadedPost {{
          createPost(
            input: {{
              text: {first_json}
              channelId: "{channel_id}"
              schedulingType: automatic
              mode: addToQueue
              aiAssisted: true
              metadata: {{
                twitter: {{
                  thread: [
                    {{ text: {first_json} }}
                    {{ text: {second_json} }}
                  ]
                }}
              }}
            }}
          ) {{
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

    result = data.get(
        "createPost",
        {},
    )

    if result.get("message"):
        raise RuntimeError(
            f"Bufferスレッド作成失敗: "
            f"{result['message']}"
        )

    post = result.get("post")

    if not post:
        raise RuntimeError(
            "Bufferスレッド作成結果が不明です: "
            f"{result}"
        )

    return post


def main():
    history = load_json_list(
        HISTORY_FILE
    )

    posted = load_json_list(
        BUFFER_HISTORY_FILE
    )

    posted_files = {
        item.get("filename")
        for item in posted
    }

    pending = [
        item
        for item in history
        if (
            item.get("filename")
            and item.get("filename")
            not in posted_files
        )
    ]

    if not pending:
        print(
            "Bufferへ送る新規記事はありません。"
        )
        return

    latest = pending[-1]
    filename = latest["filename"]

    print(
        "Buffer投稿対象:",
        filename,
    )

    channel_id = get_x_channel_id()

    (
        first_post,
        second_post,
    ) = create_thread_copy(
        latest
    )

    print("")
    print("===== Xスレッド1投目 =====")
    print(first_post)

    print("")
    print("===== Xスレッド2投目 =====")
    print(second_post)

    post = create_buffer_thread(
        channel_id,
        first_post,
        second_post,
    )

    posted.append(
        {
            "filename": filename,
            "buffer_post_id": post.get("id"),
            "due_at": post.get("dueAt"),
            "type": "twitter_thread_2_posts",
        }
    )

    BUFFER_HISTORY_FILE.write_text(
        json.dumps(
            posted,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        "Bufferスレッド予約完了:",
        post,
    )


if __name__ == "__main__":
    main()
