import os
import re
from datetime import datetime
from pathlib import Path

from google import genai


# =========================================
# 設定
# =========================================

MODEL_NAME = "gemini-2.5-flash"

SITE_NAME = "AI Trend Blog"

ARTICLE_DIR = Path("articles")


# =========================================
# Gemini
# =========================================

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY が設定されていません。")

client = genai.Client(api_key=api_key)


# =========================================
# 記事生成
# =========================================

prompt = """
あなたは日本語のAI・テクノロジー系Webメディアの編集者です。

AI、生成AI、動画生成AI、Webサービスの中から、
初心者にも役立つ記事を1本作成してください。

今回はテストなので、最新ニュースを断定する記事ではなく、
時間が経っても比較的価値が落ちにくい実用記事にしてください。

条件：

・日本語
・タイトルを付ける
・初心者向け
・誇張表現は禁止
・確認できない数字や事実を作らない
・投資助言や医療助言など高リスク分野は扱わない
・読みやすく見出しを入れる
・本文は1200〜2200文字程度
・最後に「まとめ」を入れる
・HTML形式で出力
・<html>や<body>タグは不要
・Markdownの```は付けない

出力形式：

<h1>記事タイトル</h1>

<p>導入文</p>

<h2>見出し</h2>
<p>本文</p>

<h2>見出し</h2>
<p>本文</p>

<h2>まとめ</h2>
<p>本文</p>
"""


response = client.models.generate_content(
    model=MODEL_NAME,
    contents=prompt,
)

article_html = response.text.strip()

if not article_html:
    raise RuntimeError("Geminiから記事本文を取得できませんでした。")


# =========================================
# タイトル取得
# =========================================

title_match = re.search(r"<h1>(.*?)</h1>", article_html, re.DOTALL)

if title_match:
    title = re.sub(r"<.*?>", "", title_match.group(1)).strip()
else:
    title = f"AI活用記事 {datetime.now().strftime('%Y-%m-%d')}"


# =========================================
# ファイル名作成
# =========================================

today = datetime.now().strftime("%Y-%m-%d_%H%M%S")

filename = f"{today}.html"

ARTICLE_DIR.mkdir(exist_ok=True)

filepath = ARTICLE_DIR / filename


# =========================================
# 完成HTML
# =========================================

page_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <title>{title} | {SITE_NAME}</title>

  <meta name="description"
        content="{title}について初心者向けにわかりやすく解説します。">

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
      margin-top: 36px;
      font-size: 23px;
    }}

    p {{
      font-size: 16px;
    }}

    .date {{
      color: #94a3b8;
      font-size: 13px;
      margin-bottom: 20px;
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
  {datetime.now().strftime("%Y.%m.%d")}
</div>

{article_html}

</article>

</main>

<footer>
  © 2026 {SITE_NAME}
</footer>

</body>
</html>
"""


filepath.write_text(page_html, encoding="utf-8")


print("================================")
print("記事生成成功")
print("タイトル:", title)
print("保存先:", filepath)
print("================================")
