import os
import re
import time
import html
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from google import genai
from google.genai import types


MODEL_NAME = "gemini-3.6-flash"
SITE_NAME = "AI Trend Blog"
ARTICLE_DIR = Path("articles")

MIN_SOURCES = 2

OFFICIAL_DOMAINS = (
    "openai.com",
    "help.openai.com",
    "ai.google.dev",
    "blog.google",
    "support.google.com",
    "deepmind.google",
    "developers.google.com",
    "microsoft.com",
    "support.microsoft.com",
    "adobe.com",
    "news.adobe.com",
    "youtube.com",
    "support.google.com/youtube",
)

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY が設定されていません。")

client = genai.Client(api_key=api_key)


PROMPT = """
あなたは日本のAI・テクノロジー系Webメディアの編集長です。

Google検索を使って、
AI・生成AI・動画生成AI・Webサービス関連の
現在注目する価値が高い情報を調査してください。

対象例：
- ChatGPT / OpenAI
- Gemini / Google
- Veo / Flow
- 動画生成AI
- AI画像生成
- YouTube関連
- AIを使った仕事効率化
- 新しいWebサービス
- AIサービスの料金変更
- セール・キャンペーン
- 初心者向けAI活用法

複数候補を調査し、
日本の一般ユーザーに現在もっとも役立つテーマを1つ選んでください。

重要ルール：

1. 最新情報はGoogle検索結果に基づく
2. 公式発表・公式ヘルプ・公式ドキュメントを最優先する
3. 確認できない数字・名称・仕様を作らない
4. ニュースの単純な言い換えは禁止
5. 「何が変わったのか」を書く
6. 「誰に影響するのか」を書く
7. 「実際にどう役立つのか」を書く
8. 初心者にも理解できる日本語
9. 誇張・煽りは禁止
10. 1500〜2500文字程度
11. URLを本文に生成しない
12. 情報源一覧を生成しない
13. 推測で対象範囲を拡張しない
14. 確認できた内容だけ書く
15. HTML形式
16. <html>、<head>、<body>タグは不要
17. Markdownコードフェンスは使わない

構成：

<h1>タイトル</h1>

<p>導入文</p>

<h2>今回わかったこと</h2>
<p>本文</p>

<h2>何が変わったのか</h2>
<p>本文</p>

<h2>誰に影響するのか</h2>
<p>本文</p>

<h2>実際にどう使える？</h2>
<p>本文</p>

<h2>注意点</h2>
<p>本文</p>

<h2>まとめ</h2>
<p>本文</p>
"""


def extract_sources(response):
    sources = []
    seen = set()

    try:
        metadata = response.candidates[0].grounding_metadata

        if not metadata:
            return []

        chunks = getattr(metadata, "grounding_chunks", None)

        if not chunks:
            return []

        for chunk in chunks:
            web = getattr(chunk, "web", None)

            if not web:
                continue

            url = getattr(web, "uri", None)
            title = getattr(web, "title", None)

            if not url:
                continue

            parsed = urlparse(url)

            if parsed.scheme not in ("http", "https"):
                continue

            if url in seen:
                continue

            seen.add(url)

            sources.append({
                "title": title or parsed.netloc,
                "url": url,
                "domain": parsed.netloc.lower(),
            })

    except Exception as e:
        print("情報源取得エラー:", e)

    return sources


def has_official_source(sources):
    for source in sources:
        domain = source["domain"]

        for official in OFFICIAL_DOMAINS:
            if official in domain or official in source["url"]:
                return True

    return False


def generate_valid_article():
    waits = [0, 10, 30, 60, 120]

    last_error = None

    for attempt, wait_seconds in enumerate(waits, start=1):

        if wait_seconds:
            print(f"{wait_seconds}秒待って再試行します...")
            time.sleep(wait_seconds)

        try:
            print(f"記事生成・検証：試行 {attempt}/{len(waits)}")

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=PROMPT,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            google_search=types.GoogleSearch()
                        )
                    ]
                ),
            )

            if not response.text or not response.text.strip():
                print("本文が空です。再試行します。")
                continue

            sources = extract_sources(response)

            print("取得情報源数:", len(sources))

            for source in sources:
                print("-", source["title"], source["url"])

            if len(sources) < MIN_SOURCES:
                print(
                    f"情報源が{MIN_SOURCES}件未満のため公開しません。"
                )
                continue

            if not has_official_source(sources):
                print("公式ソースが含まれていないため再試行します。")
                continue

            return response, sources

        except Exception as e:
            last_error = e
            print("生成エラー:", e)

    raise RuntimeError(
        f"品質条件を満たす記事を生成できませんでした。"
        f" 最終エラー: {last_error}"
    )


response, sources = generate_valid_article()

article_html = response.text.strip()
article_html = article_html.replace("```html", "")
article_html = article_html.replace("```", "").strip()


title_match = re.search(
    r"<h1[^>]*>(.*?)</h1>",
    article_html,
    re.DOTALL
)

if title_match:
    title = re.sub(
        r"<.*?>",
        "",
        title_match.group(1)
    ).strip()
else:
    title = f"AI最新情報 {datetime.now().strftime('%Y-%m-%d')}"


# 最大8ソース
sources = sources[:8]

source_items = []

for source in sources:
    safe_source_title = html.escape(source["title"])
    safe_source_url = html.escape(
        source["url"],
        quote=True
    )

    source_items.append(
        f'<li><a href="{safe_source_url}" '
        f'target="_blank" rel="noopener noreferrer">'
        f'{safe_source_title}</a></li>'
    )

sources_html = """
<h2>情報源</h2>
<p>
この記事の作成時にGoogle検索で参照された情報源です。
重要な仕様・料金・利用条件は一次情報もご確認ください。
</p>
<ul>
""" + "\n".join(source_items) + """
</ul>
"""


now = datetime.now()

filename = (
    now.strftime("%Y-%m-%d_%H%M%S")
    + ".html"
)

ARTICLE_DIR.mkdir(exist_ok=True)
filepath = ARTICLE_DIR / filename

safe_title = html.escape(
    title,
    quote=True
)


page_html = f"""<!DOCTYPE html>
<html lang="ja">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>{safe_title} | {SITE_NAME}</title>

<meta name="description"
      content="{safe_title}について最新情報をもとに初心者向けに解説します。">

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

ul {{
  padding-left: 24px;
}}

li {{
  margin-bottom: 10px;
}}

a {{
  word-break: break-all;
}}

.date {{
  color: #94a3b8;
  font-size: 13px;
  margin-bottom: 20px;
}}

.notice {{
  margin-top: 35px;
  padding: 16px;
  background: #f1f5f9;
  border-radius: 10px;
  color: #64748b;
  font-size: 13px;
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
<a href="../index.html">{SITE_NAME}</a>
</header>

<main>

<article>

<div class="date">
{now.strftime("%Y.%m.%d")}
</div>

{article_html}

{sources_html}

<div class="notice">
この記事はAIとGoogle検索を利用して情報整理・作成しています。
内容は公開時点の情報に基づきます。
重要な仕様・料金・利用条件などは、
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

filepath.write_text(
    page_html,
    encoding="utf-8"
)

print("")
print("================================")
print("記事生成成功")
print("タイトル:", title)
print("保存先:", filepath)
print("情報源数:", len(sources))
print("公式ソースあり:", has_official_source(sources))
print("================================")
