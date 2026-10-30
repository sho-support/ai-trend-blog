# verify_paid_info_candidates.py

import os
import re
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse, urljoin, quote_plus

import feedparser
import requests
from bs4 import BeautifulSoup
from google import genai
from gemini_budget_guard import stop_if_monthly_cap_exceeded
from gnews_decoder import decode as decode_google_news_url


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

MODEL_NAME = "gemini-3.8-flash"
FALLBACK_MODEL_NAMES = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
]

JST = timezone(timedelta(hours=9))

CANDIDATE_FILE = Path("paid_info_candidates.json")
VERIFIED_FILE = Path("verified_paid_info_candidates.json")
REPORT_DIR = Path("paid_info_verification")

MAX_CANDIDATES_PER_RUN = 10
MAX_SOURCE_CHARS = 14000
REQUEST_TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/155 Safari/537.36"
    )
}

IGNORE_EXTERNAL_DOMAINS = {
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "youtube.com",
    "youtu.be",
    "linkedin.com",
    "line.me",
    "tiktok.com",
    "google.com",
    "google.co.jp",
    "news.google.com",
}

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY が設定されていません。")

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_content_with_fallback(contents, purpose="Gemini生成"):
    last_error = None

    for model_name in [MODEL_NAME, *FALLBACK_MODEL_NAMES]:
        try:
            print(f"{purpose}: {model_name} を使用")

            # この検証スクリプトのGemini応答はすべてJSON形式。
            # プロンプトで依頼するだけでなくAPI側でもJSONを指定する。
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config={"response_mime_type": "application/json"},
            )

            # JSONが壊れている場合は成功扱いせず次のモデルへ。
            extract_json_object(response.text)
            return response

        except Exception as e:
            stop_if_monthly_cap_exceeded(e)
            last_error = e
            print(f"{purpose}エラー [{model_name}]: {e}")

    raise RuntimeError(
        f"{purpose}失敗: 全モデルで有効なJSONを取得できませんでした: {last_error}"
    )


def load_json_list(path):
    if not path.exists():
        return []

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )

        return (
            value
            if isinstance(value, list)
            else []
        )

    except Exception:
        return []


def save_json_list(path, value):
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def clean_text(text):
    return re.sub(
        r"\s+",
        " ",
        text or "",
    ).strip()


def normalize_domain(url):
    try:
        host = urlparse(url).netloc.lower()

        if host.startswith("www."):
            host = host[4:]

        return host

    except Exception:
        return ""


def same_domain_or_subdomain(host, base):
    return (
        host == base
        or host.endswith("." + base)
    )


def extract_json_object(text):
    text = (text or "").strip()
    text = (
        text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    match = re.search(r"\{", text)
    if not match:
        raise ValueError(
            "Gemini応答からJSONオブジェクトを取得できませんでした。"
        )

    # 余分な文章が後ろにあっても最初のオブジェクトのみを読む。
    # JSON構文エラーを勝手に修復・補完しない。
    result, _ = json.JSONDecoder().raw_decode(text[match.start():])
    if not isinstance(result, dict):
        raise ValueError("Gemini応答がJSONオブジェクトではありません。")
    return result


def resolve_google_news_url(url):
    if "news.google.com" not in (url or ""):
        return url

    try:
        resolved = decode_google_news_url(url)

        if (
            isinstance(resolved, str)
            and resolved.startswith("http")
        ):
            return resolved

        if isinstance(resolved, dict):
            for key in (
                "url",
                "decoded_url",
            ):
                value = resolved.get(key)

                if (
                    isinstance(value, str)
                    and value.startswith("http")
                ):
                    return value

    except Exception as e:
        print(
            "Google News URLデコード失敗:",
            e,
        )

    return url


def fetch_page(url):
    url = resolve_google_news_url(url)

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

        response.raise_for_status()

        final_url = response.url
        content_type = response.headers.get(
            "content-type",
            "",
        )

        if (
            "text/html" not in content_type
            and "<html" not in response.text[:500].lower()
        ):
            return {
                "url": final_url,
                "domain": normalize_domain(final_url),
                "title": "",
                "text": "",
                "links": [],
                "ok": False,
                "error": (
                    "HTMLではありません: "
                    + content_type
                ),
            }

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        title = clean_text(
            soup.title.get_text(
                " ",
                strip=True,
            )
            if soup.title
            else ""
        )

        links = []

        for a in soup.find_all(
            "a",
            href=True,
        ):
            href = a.get("href", "").strip()

            if not href:
                continue

            absolute = urljoin(
                final_url,
                href,
            )

            if not absolute.startswith(
                ("http://", "https://")
            ):
                continue

            links.append(
                {
                    "url": absolute,
                    "text": clean_text(
                        a.get_text(
                            " ",
                            strip=True,
                        )
                    ),
                }
            )

        for tag in soup(
            [
                "script",
                "style",
                "nav",
                "footer",
                "header",
                "aside",
                "noscript",
            ]
        ):
            tag.decompose()

        text = clean_text(
            soup.get_text(
                " ",
                strip=True,
            )
        )

        return {
            "url": final_url,
            "domain": normalize_domain(final_url),
            "title": title,
            "text": text[:MAX_SOURCE_CHARS],
            "links": links[:300],
            "ok": bool(text),
            "error": "",
        }

    except Exception as e:
        return {
            "url": url,
            "domain": normalize_domain(url),
            "title": "",
            "text": "",
            "links": [],
            "ok": False,
            "error": str(e),
        }


def google_news_search(
    query,
    max_results=10,
):
    url = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(query)}"
        "&hl=ja"
        "&gl=JP"
        "&ceid=JP:ja"
    )

    feed = feedparser.parse(url)

    results = []

    for entry in feed.entries[:max_results]:
        raw_url = getattr(
            entry,
            "link",
            "",
        )

        decoded_url = resolve_google_news_url(
            raw_url
        )

        source_obj = getattr(
            entry,
            "source",
            {},
        )

        source_name = ""

        if hasattr(
            source_obj,
            "title",
        ):
            source_name = clean_text(
                source_obj.title
            )

        results.append(
            {
                "title": clean_text(
                    getattr(
                        entry,
                        "title",
                        "",
                    )
                ),
                "url": decoded_url,
                "source": source_name,
            }
        )

    return results


def extract_entity_info(
    candidate,
    article_page,
):
    prompt = f"""
以下の有料情報候補について、
検証対象となる「商品・サービス・企業・ブランド」を特定してください。

推測で存在しない企業名やURLを作ってはいけません。

候補:
{json.dumps(candidate, ensure_ascii=False, indent=2)}

元記事タイトル:
{article_page.get("title", "")}

元記事本文:
{article_page.get("text", "")[:8000]}

次のJSONだけを返してください。

{{
  "main_entity": "主対象の商品・サービス・ブランド名",
  "company_name": "運営会社名。本文で確認できなければ空文字",
  "search_keywords": [
    "公式情報を探すための検索語1",
    "検索語2"
  ],
  "likely_official_domains": [
    "本文や明確な知識から高確度で分かる場合のみドメイン。推測なら入れない"
  ],
  "official_pages_to_find": [
    "料金",
    "キャンペーン",
    "利用規約"
  ]
}}
"""

    response = generate_content_with_fallback(
        prompt,
        purpose="公式情報探索対象の抽出",
    )

    return extract_json_object(
        response.text
    )


def collect_external_links(
    article_page,
):
    source_domain = article_page.get(
        "domain",
        "",
    )

    found = []

    for link in article_page.get(
        "links",
        [],
    ):
        url = link.get(
            "url",
            "",
        )

        domain = normalize_domain(url)

        if not domain:
            continue

        if same_domain_or_subdomain(
            domain,
            source_domain,
        ):
            continue

        if any(
            same_domain_or_subdomain(
                domain,
                ignored,
            )
            for ignored in IGNORE_EXTERNAL_DOMAINS
        ):
            continue

        found.append(
            {
                "url": url,
                "domain": domain,
                "anchor_text": link.get(
                    "text",
                    "",
                ),
            }
        )

    unique = []
    seen = set()

    for item in found:
        key = item["url"]

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    return unique[:30]


def classify_source(
    candidate,
    entity_info,
    page,
):
    prompt = f"""
あなたはファクトチェック用の情報源分類担当です。

以下のWebページが、
対象の商品・サービス・キャンペーンについて
どの種類の情報源か判定してください。

対象候補:
{json.dumps(candidate, ensure_ascii=False)}

対象企業・ブランド:
{json.dumps(entity_info, ensure_ascii=False)}

ページURL:
{page.get("url", "")}

ページタイトル:
{page.get("title", "")}

ページ本文:
{page.get("text", "")[:6000]}

判定基準:

official:
対象企業・ブランド自身が運営する公式サイト、
公式料金ページ、公式キャンペーンページ、
公式ヘルプ、公式利用規約など

primary_release:
対象企業自身が出したプレスリリース。
PR TIMESなど第三者プラットフォーム掲載でも、
企業自身の正式発表と明確に確認できる場合を含む

secondary:
新聞、ニュースサイト、ブログ、販売店、比較サイト等

unrelated:
対象と無関係

JSONだけ返してください。

{{
  "source_type": "official|primary_release|secondary|unrelated",
  "confidence": 0,
  "reason": "理由"
}}
"""

    response = generate_content_with_fallback(
        prompt,
        purpose="情報源分類",
    )

    return extract_json_object(
        response.text
    )


def build_search_queries(
    candidate,
    entity_info,
):
    queries = []

    entity = entity_info.get(
        "main_entity",
        "",
    )

    company = entity_info.get(
        "company_name",
        "",
    )

    for keyword in entity_info.get(
        "search_keywords",
        [],
    ):
        if keyword:
            queries.append(keyword)

    if entity:
        queries.extend(
            [
                f"{entity} 公式",
                f"{entity} 料金",
                f"{entity} キャンペーン",
                f"{entity} 利用規約",
                f"{entity} プレスリリース",
            ]
        )

    if company:
        queries.extend(
            [
                f"{company} {entity}",
                f"{company} 公式",
            ]
        )

    queries.append(
        candidate.get(
            "candidate_title",
            "",
        )
    )

    cleaned = []

    for query in queries:
        query = clean_text(query)

        if (
            query
            and query not in cleaned
        ):
            cleaned.append(query)

    return cleaned[:8]


def find_sources(candidate):
    article_page = fetch_page(
        candidate.get(
            "url",
            "",
        )
    )

    if not article_page.get("ok"):
        print(
            "元記事を取得できません:",
            article_page.get(
                "error",
                "",
            ),
        )

    entity_info = extract_entity_info(
        candidate,
        article_page,
    )

    print(
        "対象:",
        entity_info.get(
            "main_entity",
            "",
        ),
    )

    print(
        "運営会社:",
        entity_info.get(
            "company_name",
            "",
        ),
    )

    pages = []

    if article_page.get("ok"):
        pages.append(
            {
                **article_page,
                "discovery": "original_article",
            }
        )

    external_links = collect_external_links(
        article_page
    )

    for item in external_links[:12]:
        page = fetch_page(
            item["url"]
        )

        if page.get("ok"):
            pages.append(
                {
                    **page,
                    "discovery": "article_external_link",
                }
            )

    search_queries = build_search_queries(
        candidate,
        entity_info,
    )

    for query in search_queries:
        print(
            "公式情報検索:",
            query,
        )

        for result in google_news_search(
            query,
            max_results=6,
        ):
            page = fetch_page(
                result["url"]
            )

            if not page.get("ok"):
                continue

            pages.append(
                {
                    **page,
                    "discovery": "news_search",
                }
            )

    # Geminiが高確度の公式ドメイン候補を返した場合は
    # そのドメインを狙った検索も行う。
    for domain in entity_info.get(
        "likely_official_domains",
        [],
    ):
        domain = clean_text(domain)

        if not domain:
            continue

        query = (
            f'{entity_info.get("main_entity", "")} '
            f"site:{domain}"
        )

        for result in google_news_search(
            query,
            max_results=6,
        ):
            page = fetch_page(
                result["url"]
            )

            if page.get("ok"):
                pages.append(
                    {
                        **page,
                        "discovery": "domain_search",
                    }
                )

    unique_pages = []
    seen_urls = set()

    for page in pages:
        url = page.get(
            "url",
            "",
        )

        if (
            not url
            or url in seen_urls
        ):
            continue

        seen_urls.add(url)
        unique_pages.append(page)

    classified = []

    # APIコストと実行時間を抑えるため最大15ページ。
    for page in unique_pages[:15]:
        try:
            classification = classify_source(
                candidate,
                entity_info,
                page,
            )
        except (RuntimeError, ValueError, TypeError) as e:
            # 未分類ページを公式情報として採用しない。
            print(
                "::warning::情報源分類を保留（JSON/APIエラー）:",
                page.get("url", ""),
                type(e).__name__,
                str(e)[:250],
            )
            continue

        source_type = classification.get(
            "source_type",
            "unrelated",
        )

        if source_type == "unrelated":
            continue

        classified.append(
            {
                **page,
                "source_type": source_type,
                "source_confidence": int(
                    classification.get(
                        "confidence",
                        0,
                    )
                    or 0
                ),
                "source_reason": classification.get(
                    "reason",
                    "",
                ),
            }
        )

    priority = {
        "official": 0,
        "primary_release": 1,
        "secondary": 2,
    }

    classified.sort(
        key=lambda x: (
            priority.get(
                x.get(
                    "source_type",
                    "secondary",
                ),
                9,
            ),
            -x.get(
                "source_confidence",
                0,
            ),
        )
    )

    return (
        entity_info,
        classified[:10],
    )


def verify_candidate(
    candidate,
    entity_info,
    sources,
):
    source_payload = []

    for source in sources:
        source_payload.append(
            {
                "url": source.get(
                    "url",
                    "",
                ),
                "domain": source.get(
                    "domain",
                    "",
                ),
                "source_type": source.get(
                    "source_type",
                    "",
                ),
                "title": source.get(
                    "title",
                    "",
                ),
                "text": source.get(
                    "text",
                    "",
                )[:MAX_SOURCE_CHARS],
            }
        )

    prompt = f"""
あなたは有料note用情報の厳格なファクトチェック担当です。

与えられた情報源だけを使用してください。
知識や推測で不足部分を埋めてはいけません。

対象:
{json.dumps(entity_info, ensure_ascii=False, indent=2)}

候補:
{json.dumps(candidate, ensure_ascii=False, indent=2)}

取得ソース:
{json.dumps(source_payload, ensure_ascii=False, indent=2)}

情報源の信頼優先順位:

1. official
2. primary_release
3. secondary

【verifiedにしてよい条件】

有料記事で重要となる主要主張の大部分が、
official または primary_release で確認できること。

【partial】

主要部分は確認できるが、
価格、期限、条件、対象範囲、利用規約など
重要情報に不足がある。

【needs_manual】

二次情報しかない、
または公式・一次情報が不足している。

【rejected】

重要主張が誤っている、
期限切れ、
誇張が大きい、
候補タイトルが根拠以上に強い。

特に次を厳格に確認してください。

- 金額
- 割引率
- 還元率
- ポイント数
- キャンペーン期間
- 申込期限
- 購入期限
- 対象商品
- 対象者
- エントリー条件
- 自動更新
- 商用利用
- API料金
- 著作権・利用規約
- 「最大」
- 「過去最安」
- 「史上最大」
- 「必ず」
- 「裏技」

JSONだけ返してください。

{{
  "status": "verified|partial|needs_manual|rejected",
  "confidence": 0,
  "verified_claims": [
    {{
      "claim": "確認できた事実",
      "source_url": "根拠URL",
      "source_type": "official|primary_release|secondary"
    }}
  ],
  "missing_claims": [
    "未確認の重要事項"
  ],
  "contradictions": [
    "候補と根拠の矛盾や誇張"
  ],
  "safe_paid_title": "確認済み情報だけを使った有料記事タイトル",
  "safe_summary": "確認済みの範囲だけの要約",
  "money_value_score": 0,
  "paid_conversion_score": 0,
  "time_sensitivity_score": 0,
  "second_slot_eligible": false,
  "purchase_deadline": "YYYY-MM-DD または空文字",
  "application_deadline": "YYYY-MM-DD または空文字",
  "useful_until": "YYYY-MM-DD または空文字",
  "evergreen": false,
  "recommended_action": "publish_candidate|hold|reject",
  "reason": "判定理由"
}}
"""

    response = generate_content_with_fallback(
        prompt,
        purpose="有料情報候補の最終検証",
    )

    result = extract_json_object(
        response.text
    )

    status = result.get(
        "status",
        "needs_manual",
    )

    if status not in {
        "verified",
        "partial",
        "needs_manual",
        "rejected",
    }:
        status = "needs_manual"

    official_or_primary = [
        source
        for source in sources
        if source.get(
            "source_type"
        ) in {
            "official",
            "primary_release",
        }
    ]

    # 安全弁:
    # 一次系ソースがないのにverifiedは許可しない。
    if (
        status == "verified"
        and not official_or_primary
    ):
        status = "needs_manual"

        result["recommended_action"] = "hold"

        result["reason"] = (
            "公式または企業自身の一次発表を"
            "自動取得できなかったため、"
            "verified判定をneeds_manualへ変更。 "
            + result.get(
                "reason",
                "",
            )
        )

    result["status"] = status

    result["confidence"] = int(
        result.get(
            "confidence",
            0,
        )
        or 0
    )

    for score_key in (
        "money_value_score",
        "paid_conversion_score",
        "time_sensitivity_score",
    ):
        try:
            result[score_key] = max(
                0,
                min(
                    100,
                    int(result.get(score_key, 0) or 0),
                ),
            )
        except Exception:
            result[score_key] = 0

    result["second_slot_eligible"] = bool(
        result.get("second_slot_eligible", False)
    )

    result["evergreen"] = bool(
        result.get("evergreen", False)
    )

    return result


def build_report(
    today,
    results,
):
    lines = [
        f"# 有料情報 自動検証レポート — {today}",
        "",
        "公式サイト・企業発表・二次情報を分けて評価しています。",
        "",
        "**verified 以外は自動公開しません。**",
        "",
    ]

    if not results:
        lines.append(
            "今回、新しく検証する候補はありませんでした。"
        )

        return (
            "\n".join(lines)
            + "\n"
        )

    for i, item in enumerate(
        results,
        1,
    ):
        verification = item[
            "verification"
        ]

        lines.extend(
            [
                (
                    f"## {i}. "
                    f"{item.get('candidate_title') or item.get('title')}"
                ),
                "",
                (
                    "- 判定: **"
                    + verification.get(
                        "status",
                        "",
                    )
                    + "**"
                ),
                (
                    "- 信頼度: "
                    + str(
                        verification.get(
                            "confidence",
                            0,
                        )
                    )
                    + "/100"
                ),
                (
                    "- 推奨: "
                    + verification.get(
                        "recommended_action",
                        "hold",
                    )
                ),
                (
                    "- 分類: "
                    + item.get(
                        "category",
                        "",
                    )
                ),
                (
                    "- 安全なタイトル案: "
                    + verification.get(
                        "safe_paid_title",
                        "",
                    )
                ),
                "",
                "### 確認できた事実",
            ]
        )

        claims = verification.get(
            "verified_claims",
            [],
        )

        if claims:
            for claim in claims:
                lines.append(
                    "- "
                    + claim.get(
                        "claim",
                        "",
                    )
                    + " — "
                    + claim.get(
                        "source_url",
                        "",
                    )
                )
        else:
            lines.append("- なし")

        lines.extend(
            [
                "",
                "### 未確認事項",
            ]
        )

        missing = verification.get(
            "missing_claims",
            [],
        )

        if missing:
            for item_missing in missing:
                lines.append(
                    "- "
                    + item_missing
                )
        else:
            lines.append("- なし")

        lines.extend(
            [
                "",
                "### 矛盾・誇張",
            ]
        )

        contradictions = verification.get(
            "contradictions",
            [],
        )

        if contradictions:
            for contradiction in contradictions:
                lines.append(
                    "- "
                    + contradiction
                )
        else:
            lines.append("- なし")

        lines.extend(
            [
                "",
                "### 確認済み要約",
                "",
                verification.get(
                    "safe_summary",
                    "",
                ),
                "",
                "### 使用した情報源",
            ]
        )

        for source in item.get(
            "sources_checked",
            [],
        ):
            lines.append(
                f"- [{source.get('source_type')}] "
                f"{source.get('url')}"
            )

        lines.append("")

    return (
        "\n".join(lines)
        + "\n"
    )


def main():
    now_jst = datetime.now(JST)
    today = now_jst.date().isoformat()

    candidates = load_json_list(
        CANDIDATE_FILE
    )

    # 新規候補はすぐ検証。
    # partial / needs_manual は毎日同じものを再検証せず、
    # 緊急度 high は1日、それ以外は3日のクールダウンを置く。
    def should_verify(item):
        status = item.get("status", "")

        if status == "unverified":
            return True

        if status not in {"partial", "needs_manual"}:
            return False

        verified_at = item.get("verified_at")

        if not verified_at:
            return True

        try:
            last_checked = datetime.fromisoformat(verified_at)

            if last_checked.tzinfo is None:
                last_checked = last_checked.replace(tzinfo=JST)

            cooldown_days = (
                1
                if item.get("urgency") == "high"
                else 3
            )

            return (
                now_jst - last_checked.astimezone(JST)
            ) >= timedelta(days=cooldown_days)

        except Exception:
            return True

    pending_indexes = [
        index
        for index, item in enumerate(candidates)
        if should_verify(item)
    ][:MAX_CANDIDATES_PER_RUN]

    if not pending_indexes:
        print(
            "検証対象の候補はありません。"
        )
        return

    verified_history = load_json_list(
        VERIFIED_FILE
    )

    run_results = []

    for index in pending_indexes:
        candidate = candidates[
            index
        ]

        print("")
        print(
            "========================"
        )
        print(
            "検証:",
            candidate.get(
                "candidate_title"
            )
            or candidate.get(
                "title"
            )
        )
        print(
            "========================"
        )

        entity_info = {}
        sources = []
        try:
            entity_info, sources = find_sources(candidate)

            print("取得ソース数:", len(sources))
            print(
                "official:",
                sum(s.get("source_type") == "official" for s in sources),
            )
            print(
                "primary_release:",
                sum(s.get("source_type") == "primary_release" for s in sources),
            )

            verification = verify_candidate(
                candidate,
                entity_info,
                sources,
            )
        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            # 情報が確認できない候補をverifiedにしない。
            # 他の候補の検証まで止めないため、手動確認待ちにする。
            print(
                "::warning::候補を未検証として保留:",
                type(e).__name__,
                str(e)[:300],
            )
            verification = {
                "status": "needs_manual",
                "retry_pending": True,
                "confidence": 0,
                "verified_claims": [],
                "missing_claims": [
                    "AI応答形式または検証処理に失敗したため根拠確認が未完了"
                ],
                "contradictions": [],
                "safe_paid_title": "",
                "safe_summary": "",
                "recommended_action": "hold",
                "reason": "自動検証エラー。公式情報の確認が完了するまで販売対象外。",
            }

        record = {
            **candidate,
            "entity_info": entity_info,
            "verification": verification,
            "sources_checked": [
                {
                    "url": source.get(
                        "url",
                        "",
                    ),
                    "domain": source.get(
                        "domain",
                        "",
                    ),
                    "source_type": source.get(
                        "source_type",
                        "",
                    ),
                    "title": source.get(
                        "title",
                        "",
                    ),
                    "source_confidence": source.get(
                        "source_confidence",
                        0,
                    ),
                }
                for source in sources
            ],
            "verified_at": now_jst.isoformat(),
        }

        # 一時的なAPI/JSONエラーは次回の自動実行で再検証。
        # 有料原稿に使われるverifiedには決してしない。
        candidates[index]["status"] = (
            "unverified"
            if verification.get("retry_pending")
            else verification["status"]
        )

        candidates[index][
            "verification"
        ] = verification

        candidates[index][
            "verified_at"
        ] = now_jst.isoformat()

        candidates[index][
            "entity_info"
        ] = entity_info

        candidates[index][
            "sources_checked"
        ] = record[
            "sources_checked"
        ]

        verified_history.append(
            record
        )

        run_results.append(
            record
        )

    save_json_list(
        CANDIDATE_FILE,
        candidates,
    )

    save_json_list(
        VERIFIED_FILE,
        verified_history,
    )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = (
        REPORT_DIR
        / f"{today}.md"
    )

    report_path.write_text(
        build_report(
            today,
            run_results,
        ),
        encoding="utf-8",
    )

    counts = {
        "verified": 0,
        "partial": 0,
        "needs_manual": 0,
        "rejected": 0,
    }

    for item in run_results:
        status = (
            item[
                "verification"
            ]
            .get(
                "status",
                "needs_manual",
            )
        )

        counts[
            status
        ] = (
            counts.get(
                status,
                0,
            )
            + 1
        )

    print("")
    print(
        "========================"
    )
    print(
        "有料情報候補 自動検証完了"
    )
    print(
        "========================"
    )

    print(
        "検証件数:",
        len(
            run_results
        ),
    )

    print(
        "verified:",
        counts[
            "verified"
        ],
    )

    print(
        "partial:",
        counts[
            "partial"
        ],
    )

    print(
        "needs_manual:",
        counts[
            "needs_manual"
        ],
    )

    print(
        "rejected:",
        counts[
            "rejected"
        ],
    )

    print(
        "レポート:",
        report_path,
    )


if __name__ == "__main__":
    main()
