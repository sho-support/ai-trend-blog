import os
import re
import json
import time
import html
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent

import feedparser
import requests
from bs4 import BeautifulSoup
from google import genai


# =========================================================
# 基本設定
# =========================================================

MODEL_NAME = "gemini-3.6-flash"

SITE_NAME = "AI Trend Blog"
SITE_BASE_URL = "https://sho-support.github.io/ai-trend-blog"

GA_MEASUREMENT_ID = "G-J5ZDLF30CS"

ARTICLE_DIR = Path("articles")
INDEX_FILE = Path("index.html")
HISTORY_FILE = Path("article_history.json")
SITEMAP_FILE = Path("sitemap.xml")
ROBOTS_FILE = Path("robots.txt")

JST = timezone(timedelta(hours=9))

MAX_SOURCE_AGE_DAYS = 10
MAX_CANDIDATES = 12
REQUEST_TIMEOUT = 20

MIN_PAGE_TEXT_LENGTH = 500
MAX_SOURCE_TEXT_LENGTH = 16000


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
        "priority": 98,
    },
    {
        "name": "GitHub",
        "feed": "https://github.com/blog.atom",
        "domain": "github.blog",
        "priority": 90,
    },
]


# =========================================================
# Gemini
# =========================================================

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY が設定されていません。")

client = genai.Client(api_key=api_key)


# =========================================================
# 共通HTML / SEO
# =========================================================

SEO_START = "<!-- AI_TREND_SEO_START -->"
SEO_END = "<!-- AI_TREND_SEO_END -->"


def get_ga_tag():
    return f"""
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA_MEASUREMENT_ID}');
</script>
""".strip()


def strip_tags(value):
    return BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)


def truncate_description(value, limit=155):
    text = re.sub(r"\s+", " ", strip_tags(value)).strip()

    if len(text) <= limit:
        return text

    return text[: limit - 1].rstrip() + "…"


def filename_date(filename):
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})_", filename or "")

    if not match:
        return None

    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"


def find_meta_description(document):
    soup = BeautifulSoup(document, "html.parser")
    tag = soup.find("meta", attrs={"name": "description"})

    if tag and tag.get("content"):
        return str(tag.get("content")).strip()

    return ""


def find_h1(document):
    soup = BeautifulSoup(document, "html.parser")
    h1 = soup.find("h1")

    if not h1:
        return ""

    return h1.get_text(" ", strip=True)


def build_seo_block(
    title,
    description,
    canonical_url,
    page_type="article",
    published_date=None,
    modified_date=None,
):
    safe_title = html.escape(title, quote=True)
    safe_description = html.escape(description, quote=True)
    safe_canonical = html.escape(canonical_url, quote=True)

    lines = [
        SEO_START,
        '<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">',
        '<meta name="googlebot" content="index,follow">',
        f'<link rel="canonical" href="{safe_canonical}">',
        f'<link rel="sitemap" type="application/xml" href="{SITE_BASE_URL}/sitemap.xml">',
        f'<meta property="og:site_name" content="{html.escape(SITE_NAME, quote=True)}">',
        f'<meta property="og:title" content="{safe_title}">',
        f'<meta property="og:description" content="{safe_description}">',
        f'<meta property="og:url" content="{safe_canonical}">',
        f'<meta property="og:type" content="{"article" if page_type == "article" else "website"}">',
        '<meta name="twitter:card" content="summary">',
        f'<meta name="twitter:title" content="{safe_title}">',
        f'<meta name="twitter:description" content="{safe_description}">',
    ]

    if page_type == "article":
        published_date = published_date or datetime.now(JST).date().isoformat()
        modified_date = modified_date or published_date

        structured_data = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": description,
            "datePublished": published_date,
            "dateModified": modified_date,
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": canonical_url,
            },
            "publisher": {
                "@type": "Organization",
                "name": SITE_NAME,
                "url": SITE_BASE_URL + "/",
            },
            "author": {
                "@type": "Organization",
                "name": SITE_NAME,
                "url": SITE_BASE_URL + "/",
            },
        }

        lines.extend(
            [
                '<script type="application/ld+json">',
                json.dumps(
                    structured_data,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).replace("</", "<\\/"),
                "</script>",
            ]
        )

    lines.append(SEO_END)
    return "\n".join(lines)


def replace_managed_seo(document, seo_block):
    pattern = re.compile(
        re.escape(SEO_START) + r".*?" + re.escape(SEO_END),
        re.DOTALL,
    )

    document = pattern.sub("", document)

    if "<head>" not in document:
        return document

    return document.replace(
        "<head>",
        "<head>\n\n" + seo_block,
        1,
    )


def ensure_ga_tags():
    files = []

    if INDEX_FILE.exists():
        files.append(INDEX_FILE)

    if ARTICLE_DIR.exists():
        files.extend(ARTICLE_DIR.glob("*.html"))

    ga_tag = get_ga_tag()
    updated_count = 0

    for filepath in files:
        try:
            text = filepath.read_text(encoding="utf-8")
        except Exception as e:
            print("HTML読込失敗:", filepath, e)
            continue

        if GA_MEASUREMENT_ID in text:
            continue

        if "<head>" not in text:
            print("headタグがないためGA4追加をスキップ:", filepath)
            continue

        text = text.replace(
            "<head>",
            "<head>\n" + ga_tag,
            1,
        )

        filepath.write_text(text, encoding="utf-8")
        updated_count += 1
        print("GA4タグ追加:", filepath)

    print("GA4更新ファイル数:", updated_count)


def ensure_existing_seo_tags(history):
    print("")
    print("既存ページSEO更新開始")

    history_by_filename = {
        item.get("filename"): item
        for item in history
        if item.get("filename")
    }

    updated_count = 0

    if INDEX_FILE.exists():
        text = INDEX_FILE.read_text(encoding="utf-8")
        title = "AI・生成AIの最新情報をわかりやすく解説"
        description = (
            "OpenAI、Google、GitHubなどの公式情報をもとに、"
            "AI・生成AI・Webサービスの最新情報をわかりやすく解説するAI Trend Blogです。"
        )

        seo_block = build_seo_block(
            title=title,
            description=description,
            canonical_url=SITE_BASE_URL + "/",
            page_type="website",
        )

        new_text = replace_managed_seo(text, seo_block)

        if new_text != text:
            INDEX_FILE.write_text(new_text, encoding="utf-8")
            updated_count += 1
            print("SEO更新:", INDEX_FILE)

    if ARTICLE_DIR.exists():
        for filepath in sorted(ARTICLE_DIR.glob("*.html")):
            try:
                text = filepath.read_text(encoding="utf-8")
            except Exception as e:
                print("既存記事読込失敗:", filepath, e)
                continue

            title = find_h1(text)

            if not title:
                print("h1がないためSEO更新をスキップ:", filepath)
                continue

            description = find_meta_description(text)

            if not description:
                soup = BeautifulSoup(text, "html.parser")
                first_p = soup.find("p")
                description = truncate_description(
                    first_p.get_text(" ", strip=True) if first_p else title
                )
            else:
                description = truncate_description(description)

            canonical_url = f"{SITE_BASE_URL}/articles/{filepath.name}"

            history_item = history_by_filename.get(filepath.name, {})
            created_at = history_item.get("created_at")

            published_date = filename_date(filepath.name)

            if created_at:
                try:
                    published_date = datetime.fromisoformat(
                        created_at
                    ).date().isoformat()
                except Exception:
                    pass

            published_date = (
                published_date
                or datetime.now(JST).date().isoformat()
            )

            seo_block = build_seo_block(
                title=title,
                description=description,
                canonical_url=canonical_url,
                page_type="article",
                published_date=published_date,
                modified_date=published_date,
            )

            new_text = replace_managed_seo(text, seo_block)

            if new_text != text:
                filepath.write_text(new_text, encoding="utf-8")
                updated_count += 1
                print("SEO更新:", filepath)

    print("SEO更新ファイル数:", updated_count)


# =========================================================
# HTTP
# =========================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "Chrome/151.0 Safari/537.36 "
        "AI-Trend-Blog/1.0"
    )
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
        value = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))

        if isinstance(value, list):
            return value

        print("履歴JSONが配列ではないため空として扱います。")
        return []

    except Exception as e:
        print("履歴読込エラー:", e)
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
    text = re.sub(r"\s+", "", (title or "").lower())
    return re.sub(r"[^\wぁ-んァ-ヶ一-龠]", "", text)


def is_duplicate(title, url, history):
    normalized_new = normalize_title(title)

    for item in history:
        if item.get("url") == url:
            return True

        old_title = normalize_title(
            item.get(
                "source_title",
                item.get("title", ""),
            )
        )

        if not normalized_new or not old_title:
            continue

        if normalized_new == old_title:
            return True

        # 同一テーマのタイトル違いをある程度弾く。
        if len(normalized_new) >= 15 and len(old_title) >= 15:
            shorter = min(len(normalized_new), len(old_title))
            common_prefix = 0

            for a, b in zip(normalized_new, old_title):
                if a == b:
                    common_prefix += 1
                else:
                    break

            similarity = common_prefix / shorter

            if similarity >= 0.80:
                return True

    return False


# =========================================================
# sitemap.xml / robots.txt
# =========================================================

def history_date_map(history):
    date_map = {}

    for item in history:
        filename = item.get("filename")
        created_at = item.get("created_at")

        if not filename or not created_at:
            continue

        try:
            dt = datetime.fromisoformat(created_at)
            date_map[filename] = dt.date().isoformat()
        except Exception:
            continue

    return date_map


def generate_sitemap(history=None):
    print("")
    print("sitemap.xml 生成開始")

    if history is None:
        history = load_history()

    article_dates = history_date_map(history)

    urlset = Element(
        "urlset",
        {"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"},
    )

    if INDEX_FILE.exists():
        url = SubElement(urlset, "url")
        SubElement(url, "loc").text = SITE_BASE_URL + "/"
        SubElement(url, "lastmod").text = datetime.now(
            JST
        ).date().isoformat()

    if ARTICLE_DIR.exists():
        for filepath in sorted(ARTICLE_DIR.glob("*.html")):
            url = SubElement(urlset, "url")

            SubElement(url, "loc").text = (
                f"{SITE_BASE_URL}/articles/{filepath.name}"
            )

            history_date = article_dates.get(filepath.name)
            lastmod_value = history_date or filename_date(filepath.name)

            if not lastmod_value:
                lastmod_value = datetime.now(JST).date().isoformat()

            SubElement(url, "lastmod").text = lastmod_value

    tree = ElementTree(urlset)

    try:
        indent(tree, space="  ")
    except Exception:
        pass

    tree.write(
        SITEMAP_FILE,
        encoding="utf-8",
        xml_declaration=True,
    )

    print("sitemap.xml 生成完了:", SITEMAP_FILE)


def generate_robots():
    content = (
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {SITE_BASE_URL}/sitemap.xml\n"
    )

    ROBOTS_FILE.write_text(
        content,
        encoding="utf-8",
    )

    print("robots.txt 更新:", ROBOTS_FILE)


# =========================================================
# RSS取得
# =========================================================

def collect_candidates():
    now = datetime.now(timezone.utc)
    candidates = []

    for source in SOURCES:
        print(f"RSS取得: {source['name']}")

        try:
            feed = feedparser.parse(source["feed"])
        except Exception as e:
            print("RSS取得失敗:", source["name"], e)
            continue

        if getattr(feed, "bozo", False):
            print(
                "RSS警告:",
                source["name"],
                getattr(feed, "bozo_exception", ""),
            )

        for entry in feed.entries:
            title = getattr(entry, "title", "").strip()
            url = getattr(entry, "link", "").strip()

            if not title or not url:
                continue

            published = entry_datetime(entry)

            if published:
                age_days = (now - published).days

                if age_days > MAX_SOURCE_AGE_DAYS:
                    continue

            summary = getattr(entry, "summary", "") or ""

            summary_text = BeautifulSoup(
                summary,
                "html.parser",
            ).get_text(" ", strip=True)

            candidates.append(
                {
                    "source_name": source["name"],
                    "source_domain": source["domain"],
                    "priority": source["priority"],
                    "title": title,
                    "url": url,
                    "published": (
                        published.isoformat()
                        if published
                        else ""
                    ),
                    "summary": summary_text,
                }
            )

    candidates.sort(
        key=lambda x: (
            x["priority"],
            x["published"],
        ),
        reverse=True,
    )

    return candidates[:MAX_CANDIDATES]


# =========================================================
# ドメイン確認
# =========================================================

def domain_is_allowed(hostname, allowed_domain):
    if not hostname:
        return False

    hostname = hostname.lower().strip(".")
    allowed_domain = allowed_domain.lower().strip(".")

    return (
        hostname == allowed_domain
        or hostname.endswith("." + allowed_domain)
    )


# =========================================================
# URL・実ページ検証
# =========================================================

def validate_candidate(candidate):
    try:
        response = fetch_url(candidate["url"])
        final_url = response.url
        parsed = urlparse(final_url)

        if parsed.scheme not in ("http", "https"):
            print("無効URL:", final_url)
            return None

        if not domain_is_allowed(
            parsed.hostname,
            candidate["source_domain"],
        ):
            print(
                "公式ドメイン外へのリダイレクトを除外:",
                final_url,
            )
            return None

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        page_title = ""

        if soup.title:
            page_title = soup.title.get_text(
                " ",
                strip=True,
            )

        page_text = soup.get_text(
            " ",
            strip=True,
        )

        if len(page_text) < MIN_PAGE_TEXT_LENGTH:
            print(
                "本文が短すぎるため除外:",
                final_url,
                "文字数:",
                len(page_text),
            )
            return None

        validated = dict(candidate)
        validated["url"] = final_url
        validated["page_title"] = page_title or candidate["title"]
        validated["status_code"] = response.status_code

        print(
            "URL検証OK:",
            response.status_code,
            final_url,
        )
        print("実ページタイトル:", validated["page_title"])

        return validated

    except Exception as e:
        print(
            "URL検証失敗:",
            candidate.get("url", ""),
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
            "form",
            "noscript",
        ]
    ):
        tag.decompose()

    target = (
        soup.find("article")
        or soup.find("main")
        or soup
    )

    text = target.get_text(
        "\n",
        strip=True,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text[:MAX_SOURCE_TEXT_LENGTH]


# =========================================================
# 未使用候補
# =========================================================

def filter_unused_candidates(candidates, history):
    unused = []

    for candidate in candidates:
        if is_duplicate(
            candidate["title"],
            candidate["url"],
            history,
        ):
            print(
                "重複候補を除外:",
                candidate["title"],
            )
            continue

        unused.append(candidate)

    return unused


# =========================================================
# 候補選定
# =========================================================

def choose_topic(candidates):
    if not candidates:
        return None

    packet = []

    for index, item in enumerate(candidates, start=1):
        packet.append(
            f"""
候補{index}

媒体:
{item['source_name']}

RSSタイトル:
{item['title']}

実ページタイトル:
{item.get('page_title', item['title'])}

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

以下は、Python側で実在確認済みの公式サイトの記事候補です。

この中から、
「今、日本の一般ユーザーに記事として最も価値があるもの」
を1つだけ選んでください。

判断基準：
・新しさ
・日本の一般ユーザーへの影響
・実用性
・検索される可能性
・話題性
・読者が知ってよかったと思えるか
・1500文字以上で有益に解説する価値があるか

優先順位：
一般ユーザー向け 約70%
開発者・専門ユーザー向け 約30%

会社人事、企業PRだけの話題、
一般ユーザーにほぼ影響しない記事は優先しないでください。

回答は候補番号の数字だけにしてください。
例：
3

候補一覧：

{''.join(packet)}
"""

    waits = [0, 10, 30]

    for attempt, wait_seconds in enumerate(waits, start=1):
        if wait_seconds:
            print(
                f"{wait_seconds}秒待って候補選定を再試行..."
            )
            time.sleep(wait_seconds)

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )

            text = response.text or ""
            match = re.search(r"\d+", text)

            if match:
                number = int(match.group())

                if 1 <= number <= len(candidates):
                    return candidates[number - 1]

        except Exception as e:
            print(
                f"候補選定エラー {attempt}/{len(waits)}:",
                e,
            )

    return candidates[0]


# =========================================================
# 記事生成
# =========================================================

def generate_article(candidate, source_text):
    prompt = f"""
あなたは日本のAI・テクノロジー系Webメディアの編集者です。

以下に渡す「公式記事本文」だけを事実の根拠として、
日本の読者向けの記事を書いてください。

【絶対ルール】

・公式記事に書かれていない数字を作らない
・公式記事に書かれていない機能を作らない
・公式記事に書かれていない料金を作らない
・対象ユーザーを勝手に拡張しない
・対応国や提供時期を推測しない
・因果関係を補完しない
・公式情報から直接確認できない目的を断定しない
・ベンチマーク数値は公式本文にあるものだけ使う
・旧モデルとの比較を推測しない
・情報源URLを生成しない
・不明な点は無理に説明しない
・煽りタイトルにしない
・公式情報が専門家向けの場合、「一般ユーザーがすぐ使える」と誤解させない

ニュース本文の単純な言い換えにはせず、

・何が起きたのか
・従来と何が違うのか
・誰に関係するのか
・日本のユーザーにどう役立つのか
・注意点

を整理してください。

読みやすさは、
一般ユーザー向け 約70%
開発者向け 約30%
程度を意識してください。

専門用語には必要であれば短い説明を加えてください。

文字量はおおむね1500〜2500文字。

HTML断片だけを出力してください。

禁止：
<html>
<head>
<body>
Markdownコードフェンス
情報源一覧
架空URL

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

【RSSタイトル】
{candidate['title']}

【実ページタイトル】
{candidate.get('page_title', candidate['title'])}

【公式記事本文】
{source_text}
"""

    waits = [0, 10, 30, 60]
    last_error = None

    for attempt, wait_seconds in enumerate(waits, start=1):
        if wait_seconds:
            print(
                f"{wait_seconds}秒待って本文生成を再試行..."
            )
            time.sleep(wait_seconds)

        try:
            print(
                f"本文生成 {attempt}/{len(waits)}"
            )

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )

            text = (response.text or "").strip()
            text = text.replace("```html", "")
            text = text.replace("```", "")

            required_headings = [
                "今回のポイント",
                "何が変わった",
                "誰に関係する",
                "どう活用できる",
                "注意点",
                "まとめ",
            ]

            headings_ok = all(
                keyword in text
                for keyword in required_headings
            )

            if (
                "<h1" in text
                and len(text) > 1200
                and headings_ok
            ):
                return text

            print(
                "本文品質条件を満たさないため再試行"
            )

        except Exception as e:
            last_error = e
            print("記事生成エラー:", e)

    raise RuntimeError(
        f"記事生成失敗: {last_error}"
    )


# =========================================================
# タイトル / 説明文
# =========================================================

def extract_title(article_html):
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


def extract_description(article_html, title):
    soup = BeautifulSoup(
        article_html,
        "html.parser",
    )

    first_p = soup.find("p")

    if first_p:
        return truncate_description(
            first_p.get_text(" ", strip=True)
        )

    return truncate_description(
        f"{title}について公式情報をもとにわかりやすく解説します。"
    )


# =========================================================
# HTMLページ作成
# =========================================================

def build_page(
    title,
    description,
    article_html,
    candidate,
    filename,
    now,
):
    safe_title = html.escape(
        title,
        quote=True,
    )

    safe_description = html.escape(
        description,
        quote=True,
    )

    safe_source_title = html.escape(
        candidate.get(
            "page_title",
            candidate["title"],
        )
    )

    safe_url = html.escape(
        candidate["url"],
        quote=True,
    )

    safe_source_name = html.escape(
        candidate["source_name"]
    )

    article_url = (
        f"{SITE_BASE_URL}/articles/{filename}"
    )

    published_date = now.date().isoformat()

    seo_block = build_seo_block(
        title=title,
        description=description,
        canonical_url=article_url,
        page_type="article",
        published_date=published_date,
        modified_date=published_date,
    )

    current_year = now.strftime("%Y")

    return f"""<!DOCTYPE html>
<html lang="ja">

<head>

{get_ga_tag()}

{seo_block}

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>{safe_title} | {SITE_NAME}</title>

<meta name="description"
content="{safe_description}">

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
  box-shadow:
    0 8px 30px
    rgba(0,0,0,0.06);
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

h3 {{
  margin-top: 28px;
  font-size: 19px;
}}

p {{
  font-size: 16px;
}}

li {{
  margin-bottom: 8px;
}}

code {{
  background: #f1f5f9;
  padding: 2px 5px;
  border-radius: 5px;
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
この記事は以下の公式ページを確認したうえで作成しています。
</p>

<p>

<strong>
{safe_source_name}
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

この記事はAIを利用して公式情報を整理しています。
内容は公開時点の情報に基づきます。
重要な仕様・料金・提供地域・利用条件などは、
必ずリンク先の公式情報をご確認ください。

</div>

</article>

</main>

<footer>

© {current_year} {SITE_NAME}

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

    index_html = INDEX_FILE.read_text(
        encoding="utf-8"
    )

    marker = '<div class="article-list">'

    if marker not in index_html:
        print(
            "article-list が見つからないため一覧更新をスキップ"
        )
        return

    # 同じ記事リンクの二重挿入防止
    article_href = f"articles/{filename}"

    if article_href in index_html:
        print(
            "index.html に同じ記事が既に存在するためスキップ:",
            article_href,
        )
        return

    now = datetime.now(JST)
    safe_title = html.escape(title)
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
          <a href="{article_href}">
            {safe_title}
          </a>
        </h2>

        <p>
          最新の公式情報をもとに、
          初心者にもわかりやすく解説しています。
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

def refresh_static_files(history):
    ensure_ga_tags()
    ensure_existing_seo_tags(history)
    generate_sitemap(history)
    generate_robots()


def main():
    print("")
    print("========================")
    print("AI Trend Blog")
    print("記事生成開始")
    print("========================")
    print("")

    history = load_history()

    # 既存ページにもGA4 / SEOを反映。
    ensure_ga_tags()
    ensure_existing_seo_tags(history)
    generate_robots()

    print(
        "GA4 Measurement ID:",
        GA_MEASUREMENT_ID,
    )

    candidates = collect_candidates()

    print(
        "RSS候補数:",
        len(candidates),
    )

    if not candidates:
        print(
            "RSSから候補を取得できませんでした。"
        )
        generate_sitemap(history)
        return

    valid_candidates = []

    for candidate in candidates:
        validated = validate_candidate(candidate)

        if validated:
            valid_candidates.append(validated)

    print(
        "URL確認済み候補:",
        len(valid_candidates),
    )

    if not valid_candidates:
        print(
            "有効な公式記事候補がありません。"
        )
        generate_sitemap(history)
        return

    unused_candidates = filter_unused_candidates(
        valid_candidates,
        history,
    )

    print(
        "未使用候補:",
        len(unused_candidates),
    )

    if not unused_candidates:
        print(
            "新規記事候補がありません。"
        )
        print(
            "今回は投稿せず正常終了します。"
        )
        generate_sitemap(history)
        return

    candidate = choose_topic(
        unused_candidates
    )

    if not candidate:
        print(
            "採用可能なテーマがありませんでした。"
        )
        generate_sitemap(history)
        return

    print("")
    print("========================")
    print("採用テーマ")
    print("========================")
    print(
        "媒体:",
        candidate["source_name"],
    )
    print(
        "RSSタイトル:",
        candidate["title"],
    )
    print(
        "実ページタイトル:",
        candidate.get(
            "page_title",
            candidate["title"],
        ),
    )
    print(
        "URL:",
        candidate["url"],
    )

    source_text = extract_page_text(
        candidate["url"]
    )

    print(
        "取得本文文字数:",
        len(source_text),
    )

    if len(source_text) < MIN_PAGE_TEXT_LENGTH:
        print(
            "公式記事本文を十分取得できないため投稿しません。"
        )
        generate_sitemap(history)
        return

    article_html = generate_article(
        candidate,
        source_text,
    )

    title = extract_title(
        article_html
    )

    description = extract_description(
        article_html,
        title,
    )

    now = datetime.now(JST)

    filename = (
        now.strftime("%Y-%m-%d_%H%M%S")
        + ".html"
    )

    ARTICLE_DIR.mkdir(
        exist_ok=True
    )

    filepath = ARTICLE_DIR / filename

    page_html = build_page(
        title=title,
        description=description,
        article_html=article_html,
        candidate=candidate,
        filename=filename,
        now=now,
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

    history.append(
        {
            "title": title,
            "source_title": candidate["title"],
            "page_title": candidate.get(
                "page_title",
                candidate["title"],
            ),
            "source_name": candidate["source_name"],
            "url": candidate["url"],
            "filename": filename,
            "created_at": now.isoformat(),
        }
    )

    history = history[-1000:]
    save_history(history)

    # indexを更新した後、トップページSEOも最終更新。
    ensure_existing_seo_tags(history)

    generate_sitemap(history)
    generate_robots()

    print("")
    print("========================")
    print("記事生成成功")
    print("========================")
    print("記事タイトル:", title)
    print("保存先:", filepath)
    print("情報源:", candidate["url"])
    print(
        "実ページタイトル:",
        candidate.get(
            "page_title",
            candidate["title"],
        ),
    )
    print("GA4:", GA_MEASUREMENT_ID)
    print("Sitemap:", SITEMAP_FILE)
    print("Robots:", ROBOTS_FILE)
    print(
        "Canonical:",
        f"{SITE_BASE_URL}/articles/{filename}",
    )
    print("========================")


if __name__ == "__main__":
    main()
