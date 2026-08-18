import os
import re
import json
import time
import html
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from google import genai


# =========================================================
# 基本設定
# =========================================================

MODEL_NAME = "gemini-3.6-flash"

SITE_NAME = "AI Trend Blog"

ARTICLE_DIR = Path("articles")

INDEX_FILE = Path("index.html")

HISTORY_FILE = Path("article_history.json")

JST = timezone(timedelta(hours=9))

MAX_SOURCE_AGE_DAYS = 10

MAX_CANDIDATES = 12

REQUEST_TIMEOUT = 15


# =========================================================
# 公式情報源
# =========================================================

SOURCES = [
    {
        "name": "OpenAI",
        "feed": "https://openai.com/news/rss.xml",
        "domain": "openai.com",
        "priority": 100,
    },
    {
        "name": "Google",
        "feed": "https://blog.google/feed/",
        "domain": "blog.google",
        "priority": 95,
    },
]


# =========================================================
# Gemini
# =========================================================

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY が設定されていません。"
    )

client = genai.Client(
    api_key=api_key
)


# =========================================================
# HTTP
# =========================================================

HEADERS = {
    "User-Agent":
        "Mozilla/5.0 AI-Trend-Blog/1.0"
}


def fetch_url(url):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
    )

    response.raise_for_status()

    return response


# =========================================================
# 日付処理
# =========================================================

def entry_datetime(entry):

    structs = [
        getattr(entry, "published_parsed", None),
        getattr(entry, "updated_parsed", None),
    ]

    for value in structs:

        if value:

            return datetime(
                *value[:6],
                tzinfo=timezone.utc,
            )

    return None


# =========================================================
# 履歴
# =========================================================

def load_history():

    if not HISTORY_FILE.exists():
        return []

    try:
        return json.loads(
            HISTORY_FILE.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return []


def save_history(history):

    HISTORY_FILE.write_text(
        json.dumps(
            history,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def normalize_title(title):

    text = re.sub(
        r"\s+",
        "",
        title.lower()
    )

    text = re.sub(
        r"[^\wぁ-んァ-ヶ一-龠]",
        "",
        text
    )

    return text


def is_duplicate(title, url, history):

    nt = normalize_title(title)

    for item in history:

        if item.get("url") == url:
            return True

        old_title = normalize_title(
            item.get("title", "")
        )

        if nt and old_title:

            if nt == old_title:
                return True

            shorter = min(
                len(nt),
                len(old_title)
            )

            if shorter >= 15:

                common = sum(
                    1
                    for a, b
                    in zip(nt, old_title)
                    if a == b
                )

                similarity = (
                    common /
                    max(len(nt), len(old_title))
                )

                if similarity > 0.82:
                    return True

    return False


# =========================================================
# RSS取得
# =========================================================

def collect_candidates():

    now = datetime.now(timezone.utc)

    candidates = []

    for source in SOURCES:

        print(
            f"RSS取得: {source['name']}"
        )

        feed = feedparser.parse(
            source["feed"]
        )

        for entry in feed.entries:

            title = (
                getattr(entry, "title", "")
                .strip()
            )

            url = (
                getattr(entry, "link", "")
                .strip()
            )

            if not title or not url:
                continue

            published = entry_datetime(
                entry
            )

            if published:

                age = (
                    now - published
                ).days

                if age > MAX_SOURCE_AGE_DAYS:
                    continue

            summary = (
                getattr(entry, "summary", "")
                or ""
            )

            candidates.append({
                "source_name":
                    source["name"],

                "priority":
                    source["priority"],

                "title":
                    title,

                "url":
                    url,

                "published":
                    (
                        published.isoformat()
                        if published
                        else ""
                    ),

                "summary":
                    BeautifulSoup(
                        summary,
                        "html.parser"
                    ).get_text(
                        " ",
                        strip=True
                    ),
            })

    candidates.sort(
        key=lambda x: (
            x["priority"],
            x["published"],
        ),
        reverse=True,
    )

    return candidates[
        :MAX_CANDIDATES
    ]


# =========================================================
# URL検証
# =========================================================

def validate_candidate(candidate):

    try:

        response = fetch_url(
            candidate["url"]
        )

        final_url = response.url

        parsed = urlparse(
            final_url
        )

        if parsed.scheme not in (
            "http",
            "https",
        ):
            return None

        candidate["url"] = final_url

        candidate["status_code"] = (
            response.status_code
        )

        return candidate

    except Exception as e:

        print(
            "URL取得失敗:",
            candidate["url"],
            e,
        )

        return None


# =========================================================
# 記事本文抽出
# =========================================================

def extract_page_text(url):

    response = fetch_url(url)

    soup = BeautifulSoup(
        response.text,
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

    text = soup.get_text(
        "\n",
        strip=True,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text[:14000]


# =========================================================
# 候補選定
# =========================================================

def choose_topic(
    candidates,
    history
):

    available = []

    for candidate in candidates:

        if is_duplicate(
            candidate["title"],
            candidate["url"],
            history,
        ):
            continue

        available.append(
            candidate
        )

    if not available:

        raise RuntimeError(
            "新規記事候補がありません。"
        )

    packet = []

    for index, item in enumerate(
        available,
        start=1,
    ):

        packet.append(
            f"""
候補{index}

媒体:
{item['source_name']}

タイトル:
{item['title']}

公開日時:
{item['published']}

概要:
{item['summary']}

URL:
{item['url']}
"""
        )

    prompt = f"""
あなたは日本向けAI・テクノロジー情報サイトの編集長です。

次の公式情報候補から、
「今、日本の一般ユーザーに記事として最も価値があるもの」
を1つだけ選んでください。

判断基準：

・新しさ
・日本の一般ユーザーへの影響
・実用性
・検索される可能性
・単なる企業ニュースではなく読者に役立つか
・記事として1500文字以上説明する価値があるか

広告的な話題や会社人事など、
一般ユーザーにほぼ関係のないものは優先しないでください。

回答は候補番号だけ。
例：
3

候補一覧：

{''.join(packet)}
"""

    for attempt in range(3):

        try:

            response = (
                client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt,
                )
            )

            match = re.search(
                r"\d+",
                response.text
            )

            if match:

                number = int(
                    match.group()
                )

                if (
                    1
                    <= number
                    <= len(available)
                ):
                    return available[
                        number - 1
                    ]

        except Exception as e:

            print(
                "候補選定エラー:",
                e
            )

            time.sleep(
                10 * (
                    attempt + 1
                )
            )

    return available[0]


# =========================================================
# 記事生成
# =========================================================

def generate_article(
    candidate,
    source_text
):

    prompt = f"""
あなたは日本のAI・テクノロジー系Webメディアの編集者です。

以下の「公式情報」だけを根拠として、
日本の一般ユーザー向けの記事を書いてください。

【最重要】

この公式情報に書かれていない
数字・機能・名称・対象ユーザー・料金・利用条件を
推測してはいけません。

分からないことは書かないでください。

ニュース内容を単に日本語で言い換えるだけではなく、

・何が起きたか
・以前と何が違うか
・誰に関係するか
・日本のユーザーにどう役立つか
・注意点

まで解説してください。

情報源URLを本文には書かないでください。
情報源はPython側で追加します。

1500〜2500文字程度。

HTML断片だけを出力してください。
<html>、<body>、Markdownコードフェンスは禁止。

構成：

<h1>自然で検索意図に合うタイトル</h1>

<p>導入文</p>

<h2>今回のポイント</h2>

<h2>何が変わった？</h2>

<h2>誰に関係する？</h2>

<h2>どう活用できる？</h2>

<h2>注意点</h2>

<h2>まとめ</h2>


【公式媒体】

{candidate['source_name']}


【公式記事タイトル】

{candidate['title']}


【公式記事本文】

{source_text}
"""

    waits = [
        0,
        10,
        30,
        60,
    ]

    last_error = None

    for attempt, wait_seconds in enumerate(
        waits,
        start=1,
    ):

        if wait_seconds:

            print(
                f"{wait_seconds}秒待って再試行..."
            )

            time.sleep(
                wait_seconds
            )

        try:

            print(
                f"本文生成 {attempt}/{len(waits)}"
            )

            response = (
                client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt,
                )
            )

            text = (
                response.text
                or ""
            ).strip()

            text = text.replace(
                "```html",
                ""
            )

            text = text.replace(
                "```",
                ""
            )

            if (
                "<h1" in text
                and len(text) > 1200
            ):
                return text

        except Exception as e:

            last_error = e

            print(
                "記事生成エラー:",
                e
            )

    raise RuntimeError(
        f"記事生成失敗: {last_error}"
    )


# =========================================================
# タイトル取得
# =========================================================

def extract_title(
    article_html
):

    match = re.search(
        r"<h1[^>]*>(.*?)</h1>",
        article_html,
        re.DOTALL,
    )

    if match:

        return re.sub(
            r"<.*?>",
            "",
            match.group(1),
        ).strip()

    return "AI最新情報"


# =========================================================
# HTMLページ作成
# =========================================================

def build_page(
    title,
    article_html,
    candidate,
):

    now = datetime.now(JST)

    safe_title = html.escape(
        title,
        quote=True,
    )

    safe_source_title = (
        html.escape(
            candidate["title"]
        )
    )

    safe_url = html.escape(
        candidate["url"],
        quote=True,
    )

    return f"""<!DOCTYPE html>
<html lang="ja">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>{safe_title} | {SITE_NAME}</title>

<meta name="description"
content="{safe_title}について公式情報をもとにわかりやすく解説します。">

<style>

* {{
box-sizing: border-box;
}}

body {{
margin: 0;
font-family:
-apple-system,
BlinkMacSystemFont,
"Segoe UI",
"Noto Sans JP",
sans-serif;
background: #f5f7fb;
color: #1d2433;
line-height: 1.9;
}}

header {{
background: #111827;
padding: 20px;
}}

header a {{
color: white;
text-decoration: none;
font-size: 22px;
font-weight: 800;
}}

main {{
max-width: 850px;
margin: 35px auto;
padding: 0 20px;
}}

article {{
background: white;
padding: 35px;
border-radius: 18px;
box-shadow: 0 8px 30px rgba(0,0,0,0.06);
}}

h1 {{
font-size: 32px;
line-height: 1.4;
margin-top: 0;
}}

h2 {{
margin-top: 38px;
font-size: 23px;
}}

p {{
font-size: 16px;
}}

.source-box {{
margin-top: 40px;
padding: 20px;
background: #f1f5f9;
border-radius: 12px;
}}

.source-box a {{
word-break: break-all;
}}

.notice {{
margin-top: 20px;
font-size: 13px;
color: #64748b;
}}

footer {{
text-align: center;
color: #94a3b8;
padding: 30px 20px;
}}

@media (max-width: 700px) {{

article {{
padding: 24px;
}}

h1 {{
font-size: 26px;
}}

}}

</style>

</head>

<body>

<header>

<a href="../index.html">
{SITE_NAME}
</a>

</header>

<main>

<article>

<div style="
color:#94a3b8;
font-size:13px;
margin-bottom:20px;
">

{now.strftime("%Y.%m.%d")}

</div>

{article_html}

<div class="source-box">

<h2>情報源</h2>

<p>
この記事は以下の公式情報をもとに作成しています。
</p>

<p>

<strong>
{candidate['source_name']}
</strong>

<br>

<a
href="{safe_url}"
target="_blank"
rel="noopener noreferrer"
>

{safe_source_title}

</a>

</p>

</div>

<div class="notice">

この記事はAIを利用して情報を整理しています。
重要な仕様・料金・利用条件は、
必ずリンク先の公式情報をご確認ください。

</div>

</article>

</main>

<footer>

© 2026 {SITE_NAME}

</footer>

</body>

</html>
"""


# =========================================================
# index.html 更新
# =========================================================

def update_index(
    title,
    filename,
    candidate,
):

    if not INDEX_FILE.exists():
        print(
            "index.html がないため一覧更新をスキップ"
        )
        return

    index_html = (
        INDEX_FILE.read_text(
            encoding="utf-8"
        )
    )

    marker = (
        '<div class="article-list">'
    )

    if marker not in index_html:

        print(
            "article-list が見つからないため一覧更新をスキップ"
        )

        return

    now = datetime.now(JST)

    safe_title = html.escape(
        title
    )

    safe_source = html.escape(
        candidate["source_name"]
    )

    card = f"""
      <article class="article-card">
        <div class="meta">
          {now.strftime("%Y.%m.%d")}
          ｜ {safe_source}
        </div>

        <h2>
          <a href="articles/{filename}">
            {safe_title}
          </a>
        </h2>

        <p>
          最新の公式情報をもとに、
          初心者向けにわかりやすく解説しています。
        </p>
      </article>
"""

    index_html = index_html.replace(
        marker,
        marker + "\n" + card,
        1,
    )

    INDEX_FILE.write_text(
        index_html,
        encoding="utf-8",
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print("")
    print("==========")
    print("AI Trend Blog")
    print("記事生成開始")
    print("==========")
    print("")

    history = load_history()

    candidates = collect_candidates()

    print(
        "候補数:",
        len(candidates)
    )

    valid_candidates = []

    for candidate in candidates:

        validated = (
            validate_candidate(
                candidate
            )
        )

        if validated:
            valid_candidates.append(
                validated
            )

    print(
        "URL確認済み候補:",
        len(valid_candidates)
    )

    candidate = choose_topic(
        valid_candidates,
        history,
    )

    print("")
    print("採用テーマ")
    print(candidate["title"])
    print(candidate["url"])
    print("")

    source_text = extract_page_text(
        candidate["url"]
    )

    if len(source_text) < 500:

        raise RuntimeError(
            "公式記事本文を十分取得できませんでした。"
        )

    article_html = generate_article(
        candidate,
        source_text,
    )

    title = extract_title(
        article_html
    )

    now = datetime.now(JST)

    filename = (
        now.strftime(
            "%Y-%m-%d_%H%M%S"
        )
        + ".html"
    )

    ARTICLE_DIR.mkdir(
        exist_ok=True
    )

    filepath = (
        ARTICLE_DIR /
        filename
    )

    page_html = build_page(
        title,
        article_html,
        candidate,
    )

    filepath.write_text(
        page_html,
        encoding="utf-8",
    )

    update_index(
        title,
        filename,
        candidate,
    )

    history.append({
        "title":
            title,

        "source_title":
            candidate["title"],

        "url":
            candidate["url"],

        "filename":
            filename,

        "created_at":
            now.isoformat(),
    })

    save_history(
        history
    )

    print("")
    print("========================")
    print("記事生成成功")
    print("========================")
    print("タイトル:", title)
    print("保存先:", filepath)
    print(
        "情報源:",
        candidate["url"]
    )
    print("========================")


if __name__ == "__main__":
    main()
