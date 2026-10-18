import os
import re
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from bs4 import BeautifulSoup
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

MODEL_NAME = "gemini-3.8-flash"
FALLBACK_MODEL_NAMES = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
]

SITE_BASE_URL = "https://sho-support.github.io/ai-trend-blog"
ARTICLE_HISTORY_FILE = Path("article_history.json")
NOTE_HISTORY_FILE = Path("note_draft_history.json")
ARTICLE_DIR = Path("articles")
NOTE_DRAFT_DIR = Path("note_drafts")

JST = timezone(timedelta(hours=9))

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY が設定されていません。")

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_content_with_fallback(contents, purpose="Gemini生成"):
    last_error = None
    for model_name in [MODEL_NAME, *FALLBACK_MODEL_NAMES]:
        try:
            print(f"{purpose}: {model_name} を使用")
            return client.models.generate_content(model=model_name, contents=contents)
        except Exception as e:
            last_error = e
            print(f"{purpose}エラー [{model_name}]: {e}")
    raise RuntimeError(f"{purpose}失敗: 全モデルで生成できませんでした: {last_error}")


def load_json_list(path):
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except Exception:
        return []


def save_json_list(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def article_text(filename):
    path = ARTICLE_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"記事が見つかりません: {path}")
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


def slugify_for_filename(text):
    text = re.sub(r'[\\/:*?"<>|]+', "_", text)
    text = re.sub(r"\s+", "_", text).strip("._ ")
    return text[:70] or "note_draft"


def extract_generated_text(response):
    text = (response.text or "").strip()
    return text.replace("```markdown", "").replace("```", "").strip()


def main():
    now_jst = datetime.now(JST)
    today = now_jst.date().isoformat()

    article_history = load_json_list(ARTICLE_HISTORY_FILE)
    note_history = load_json_list(NOTE_HISTORY_FILE)

    if any(item.get("draft_date_jst") == today for item in note_history):
        print("本日はすでにnote無料記事の下書きを作成済みです。")
        return

    drafted_files = {item.get("article_filename") for item in note_history}
    candidates = [
        item for item in article_history
        if item.get("filename") and item.get("filename") not in drafted_files
    ]

    if not candidates:
        print("note下書き化する新規記事はありません。")
        return

    article = candidates[-1]
    filename = article["filename"]
    title = article.get("title", "")
    source_name = article.get("source_name", "")
    source_url = article.get("url", "")
    article_url = f"{SITE_BASE_URL}/articles/{filename}"
    body = article_text(filename)[:9000]

    prompt = f'''
あなたは日本向けメディア「AI Trend Blog」のnote編集担当です。

以下の既存ブログ記事だけを根拠に、
note向けの「無料集客記事」を日本語で作ってください。

【目的】
・note内で単独でも役立つ記事にする
・AIニュースを難しくしすぎず、一般の人にも読みやすくする
・最後にAI Trend Blogの元記事へ自然に誘導する
・有料noteではない
・売り込みすぎない

【絶対ルール】
・元記事にない事実、数字、料金、提供地域、機能を追加しない
・推測を事実のように書かない
・元記事と矛盾する内容を書かない
・SEO目的の不自然なキーワード詰め込みをしない
・「完全版」「絶対」「必ず」など過剰な煽りは禁止
・元記事の丸写しは避け、note向けに構成し直す

【構成】
1. note向けタイトル
2. 2〜4文の導入
3. 「今回のポイント」3項目
4. 見出し2〜4個で本文
5. 「こんな人はチェック」または「今後見るべきポイント」
6. まとめ
7. 最後に以下の元記事URLを1回だけ掲載

元記事URL:
{article_url}

【文体】
・です／ます調
・やわらかいが軽すぎない
・1段落を短めにする
・全体で900〜1,500文字程度
・Markdown形式
・タイトルは先頭を「# 」にする
・ハッシュタグは付けない

元記事タイトル:
{title}

情報源:
{source_name}

情報源URL:
{source_url}

元記事本文:
{body}
'''

    response = generate_content_with_fallback(prompt, purpose="note無料記事下書き生成")
    draft = extract_generated_text(response)

    if not draft:
        raise RuntimeError("note下書きが空でした。")

    NOTE_DRAFT_DIR.mkdir(parents=True, exist_ok=True)

    draft_filename = f"{today}_{slugify_for_filename(title)}.md"
    draft_path = NOTE_DRAFT_DIR / draft_filename
    draft_path.write_text(draft + "\n", encoding="utf-8")

    note_history.append({
        "article_filename": filename,
        "article_title": title,
        "draft_filename": draft_filename,
        "draft_date_jst": today,
        "created_at": now_jst.isoformat(),
        "status": "draft",
        "type": "free_note",
    })

    save_json_list(NOTE_HISTORY_FILE, note_history)

    print("========================")
    print("note無料記事の下書き生成成功")
    print("========================")
    print("元記事:", filename)
    print("保存先:", draft_path)
    print("種別: free_note")
    print("状態: draft")


if __name__ == "__main__":
    main()
