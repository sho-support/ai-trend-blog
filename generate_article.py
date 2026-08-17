import os
import re
import time
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types


MODEL_NAME = "gemini-3.6-flash"
SITE_NAME = "AI Trend Blog"
ARTICLE_DIR = Path("articles")

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY が設定されていません。")

client = genai.Client(api_key=api_key)


prompt = """
あなたは日本のAI・テクノロジー系Webメディアの編集長です。

Google検索を使って、現在ネット上で注目する価値がある
AI・生成AI・動画生成AI・Webサービス関連の情報を調査してください。

対象例：
- ChatGPT / OpenAI
- Gemini / Google
- Veo
- 動画生成AI
- AI画像生成
- YouTube関連
- AIを使った仕事効率化
- 新しいWebサービス
- AIサービスの料金変更
- セール・キャンペーン
- 初心者向けAI活用法

最初に複数の候補を調査し、
その中から「日本の一般ユーザーに今もっとも役立つテーマ」を1つ選んでください。

記事作成ルール：

1. 最新情報の場合は必ずWeb検索結果に基づく
2. 可能な限り公式サイト・公式発表を優先する
3. 確認できない事実や数字を作らない
4. ニュースの単純な言い換えは禁止
5. 「何が変わったのか」を説明する
6. 「誰に関係するのか」を説明する
7. 「実際にどう役立つのか」を説明する
8. 初心者でも理解できる日本語
9. 誇張・煽りは禁止
10. 1500～2500文字程度
11. 情報源を記事末尾に記載する
12. URLは実際に検索で確認したものだけ使用する
13. HTML形式
14. <html>、<head>、<body>タグは出力しない
15. Markdownの ``` は使用しない

以下の構成を基本にしてください。

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

<h2>情報源</h2>

<ul>
<li><a href="実際のURL">情報源名</a></li>
</ul>
"""


def generate_with_retry():
    waits = [0, 10, 30, 60, 120]

    last_error = None

    for attempt, wait_seconds in enumerate(waits, start=1):

        if wait_seconds:
            print(f"{wait_seconds}秒待って再試行します...")
            time.sleep(wait_seconds)

        try:
            print(f"Gemini記事生成：試行 {attempt}/{len(waits)}")

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            google_search=types.GoogleSearch()
                        )
                    ]
                ),
            )

            if response.text and response.text.strip():
                return response.text.strip()

        except Exception as e:
            last_error = e
            print(f"生成エラー: {e}")

    raise RuntimeError(
        f"記事生成に失敗しました。最終エラー: {last_error}"
    )


article_html = generate_with_retry()


# Markdownコードフェンス対策
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


now = datetime.now()
filename = now.strftime("%Y-%m-%d_%H%M%S") + ".html"

ARTICLE_DIR.mkdir(exist_ok=True)

filepath = ARTICLE_DIR / filename


safe_title = (
    title.replace("&", "&amp;")
         .replace('"', "&quot;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
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

<div class="notice">
この記事はAIを利用して情報整理・作成しています。
重要な情報はリンク先の公式情報もあわせてご確認ください。
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
print("================================")
