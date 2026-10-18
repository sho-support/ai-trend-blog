import os
import re
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse, quote_plus

import feedparser
import requests
from bs4 import BeautifulSoup
from google import genai
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
MAX_SOURCE_CHARS = 12000
REQUEST_TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/155 Safari/537.36"
    )
}

OFFICIAL_DOMAIN_RULES = [
    (["amazon", "プライム", "kindle", "music unlimited"], [
        "amazon.co.jp", "amazon.com", "aboutamazon.jp"
    ]),
    (["楽天市場", "楽天モバイル", "楽天", "rakuten"], [
        "rakuten.co.jp", "corp.rakuten.co.jp", "network.mobile.rakuten.co.jp"
    ]),
    (["sony", "ソニー", "α", "alpha"], [
        "sony.jp", "sony.com"
    ]),
    (["x収益", "x（旧twitter）", "twitter", "xの"], [
        "x.com", "help.x.com", "business.x.com"
    ]),
    (["microsoft", "powerpoint", "copilot"], [
        "microsoft.com"
    ]),
    (["openai", "chatgpt", "codex"], [
        "openai.com"
    ]),
    (["google", "gemini"], [
        "google.com", "blog.google"
    ]),
]

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY が設定されていません。")

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_content_with_fallback(contents, purpose="Gemini生成"):
    last_error = None

    for model_name in [MODEL_NAME, *FALLBACK_MODEL_NAMES]:
        try:
            print(f"{purpose}: {model_name} を使用")
            return client.models.generate_content(
                model=model_name,
                contents=contents,
            )
        except Exception as e:
            last_error = e
            print(f"{purpose}エラー [{model_name}]: {e}")

    raise RuntimeError(
        f"{purpose}失敗: 全モデルで生成できませんでした: {last_error}"
    )


def load_json_list(path):
    if not path.exists():
        return []

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except Exception:
        return []


def save_json_list(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def normalize_domain(url):
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def domain_matches(host, allowed):
    return host == allowed or host.endswith("." + allowed)


def official_domains_for_candidate(candidate):
    haystack = " ".join([
        candidate.get("title", ""),
        candidate.get("candidate_title", ""),
        candidate.get("summary", ""),
        candidate.get("source", ""),
    ]).lower()

    domains = []

    for keywords, mapped_domains in OFFICIAL_DOMAIN_RULES:
        if any(keyword.lower() in haystack for keyword in keywords):
            domains.extend(mapped_domains)

    return list(dict.fromkeys(domains))


def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def resolve_google_news_url(url):
    if "news.google.com" not in (url or ""):
        return url

    try:
        resolved = decode_google_news_url(url)

        if isinstance(resolved, str) and resolved.startswith("http"):
            return resolved

        # 実装差異に備える
        if isinstance(resolved, dict):
            for key in ("url", "decoded_url"):
                value = resolved.get(key)
                if isinstance(value, str) and value.startswith("http"):
                    return value

    except Exception as e:
        print("Google News URLデコード失敗:", e)

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
        content_type = response.headers.get("content-type", "")

        if (
            "text/html" not in content_type
            and "<html" not in response.text[:500].lower()
        ):
            return {
                "url": final_url,
                "domain": normalize_domain(final_url),
                "title": "",
                "text": "",
                "ok": False,
                "error": f"HTMLではありません: {content_type}",
            }

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(
            ["script", "style", "nav", "footer", "header", "aside", "noscript"]
        ):
            tag.decompose()

        title = clean_text(
            soup.title.get_text(" ", strip=True)
            if soup.title else ""
        )
        text = clean_text(
            soup.get_text(" ", strip=True)
        )

        return {
            "url": final_url,
            "domain": normalize_domain(final_url),
            "title": title,
            "text": text[:MAX_SOURCE_CHARS],
            "ok": bool(text),
            "error": "",
        }

    except Exception as e:
        return {
            "url": url,
            "domain": normalize_domain(url),
            "title": "",
            "text": "",
            "ok": False,
            "error": str(e),
        }


def google_news_search(query, max_results=8):
    url = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(query)}&hl=ja&gl=JP&ceid=JP:ja"
    )

    feed = feedparser.parse(url)
    results = []

    for entry in feed.entries[:max_results]:
        raw_url = getattr(entry, "link", "")
        decoded_url = resolve_google_news_url(raw_url)

        results.append({
            "title": clean_text(getattr(entry, "title", "")),
            "url": decoded_url,
            "source": clean_text(
                getattr(getattr(entry, "source", {}), "title", "")
                if hasattr(getattr(entry, "source", {}), "title")
                else ""
            ),
        })

    return results


def find_official_sources(candidate):
    allowed_domains = official_domains_for_candidate(candidate)
    sources = []

    original = fetch_page(candidate.get("url", ""))

    if original.get("ok"):
        original["source_type"] = (
            "official"
            if any(
                domain_matches(original["domain"], d)
                for d in allowed_domains
            )
            else "secondary"
        )
        sources.append(original)

    search_seed = (
        candidate.get("candidate_title")
        or candidate.get("title")
        or ""
    )

    for domain in allowed_domains:
        query = f'{search_seed} site:{domain}'

        for result in google_news_search(query, max_results=5):
            page = fetch_page(result["url"])

            if not page.get("ok"):
                continue

            if not domain_matches(page["domain"], domain):
                continue

            page["source_type"] = "official"

            if all(
                existing.get("url") != page.get("url")
                for existing in sources
            ):
                sources.append(page)

            if len([
                s for s in sources
                if s.get("source_type") == "official"
            ]) >= 3:
                break

        if len([
            s for s in sources
            if s.get("source_type") == "official"
        ]) >= 3:
            break

    return sources, allowed_domains


def extract_json_object(text):
    text = (text or "").strip()
    text = text.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\{[\s\S]*\}", text)

    if not match:
        raise ValueError(
            "Gemini応答からJSONオブジェクトを取得できませんでした。"
        )

    return json.loads(match.group(0))


def verify_candidate(candidate, sources, allowed_domains):
    source_payload = []

    for source in sources:
        source_payload.append({
            "url": source.get("url", ""),
            "domain": source.get("domain", ""),
            "source_type": source.get("source_type", ""),
            "title": source.get("title", ""),
            "text": source.get("text", "")[:MAX_SOURCE_CHARS],
        })

    prompt = f"""
あなたは有料情報商品のファクトチェック担当です。

以下の候補を、与えられたソースだけで厳格に検証してください。
あなた自身の知識や推測で不足情報を補ってはいけません。

【判定ルール】
- verified:
  有料記事で重要になる主要事実が公式・一次情報で確認できる
- partial:
  一部は確認できるが、価格・期限・条件など重要事項に未確認が残る
- rejected:
  候補の重要主張がソースと矛盾する、期限切れ、誇張が大きい
- needs_manual:
  公式・一次情報が十分取得できず自動判定できない

【特に厳格に確認するもの】
- 金額
- 割引率
- ポイント数
- 開催期間・終了日
- 対象者
- エントリー条件
- 自動更新
- 商用利用条件
- 「最大」「過去最安」「史上最大」「必ず得」等の強い表現

公式ドメイン候補:
{json.dumps(allowed_domains, ensure_ascii=False)}

候補:
{json.dumps(candidate, ensure_ascii=False, indent=2)}

取得ソース:
{json.dumps(source_payload, ensure_ascii=False, indent=2)}

次のJSONオブジェクトだけを返してください。

{{
  "status": "verified|partial|rejected|needs_manual",
  "confidence": 0,
  "verified_claims": [
    {{
      "claim": "確認できた事実",
      "source_url": "根拠URL"
    }}
  ],
  "missing_claims": ["まだ確認できない重要事項"],
  "contradictions": ["矛盾や誇張。なければ空配列"],
  "safe_paid_title": "確認済み情報だけで作った安全な有料記事タイトル案",
  "safe_summary": "確認済みの範囲だけで120〜250文字程度の要約",
  "recommended_action": "publish_candidate|hold|reject",
  "reason": "判定理由"
}}
"""

    response = generate_content_with_fallback(
        prompt,
        purpose="有料情報候補のファクトチェック",
    )

    result = extract_json_object(response.text)

    status = result.get("status", "needs_manual")

    if status not in {
        "verified",
        "partial",
        "rejected",
        "needs_manual",
    }:
        status = "needs_manual"

    result["status"] = status
    result["confidence"] = int(
        result.get("confidence", 0) or 0
    )

    return result


def build_report(today, results):
    lines = [
        f"# 有料情報 自動検証レポート — {today}",
        "",
        "このレポートは候補情報を公式・一次情報優先で自動検証した結果です。",
        "**verified 以外は、そのまま有料noteへ公開しません。**",
        "",
    ]

    if not results:
        lines.append(
            "今回、新しく検証する候補はありませんでした。"
        )
        return "\n".join(lines) + "\n"

    for i, item in enumerate(results, 1):
        v = item["verification"]

        lines.extend([
            f"## {i}. {item.get('candidate_title') or item.get('title')}",
            "",
            f"- 判定: **{v.get('status')}**",
            f"- 信頼度: {v.get('confidence', 0)}/100",
            f"- 推奨: {v.get('recommended_action', 'hold')}",
            f"- 分類: {item.get('category', '')}",
            f"- 元候補スコア: {item.get('score', 0)}/100",
            f"- 安全なタイトル案: {v.get('safe_paid_title', '')}",
            f"- 判定理由: {v.get('reason', '')}",
            "",
            "### 確認できた事実",
        ])

        verified_claims = v.get("verified_claims") or []

        if verified_claims:
            for claim in verified_claims:
                lines.append(
                    f"- {claim.get('claim', '')} — "
                    f"{claim.get('source_url', '')}"
                )
        else:
            lines.append("- なし")

        lines.extend(["", "### 未確認事項"])

        missing = v.get("missing_claims") or []

        if missing:
            for claim in missing:
                lines.append(f"- {claim}")
        else:
            lines.append("- なし")

        lines.extend(["", "### 矛盾・誇張チェック"])

        contradictions = v.get("contradictions") or []

        if contradictions:
            for claim in contradictions:
                lines.append(f"- {claim}")
        else:
            lines.append("- なし")

        lines.extend([
            "",
            "### 確認済み範囲の要約",
            "",
            v.get("safe_summary", ""),
            "",
        ])

    return "\n".join(lines) + "\n"


def main():
    now_jst = datetime.now(JST)
    today = now_jst.date().isoformat()

    candidates = load_json_list(CANDIDATE_FILE)

    # needs_manual も再検証対象にする。
    pending_indexes = [
        i
        for i, item in enumerate(candidates)
        if item.get("status") in {"unverified", "needs_manual"}
    ][:MAX_CANDIDATES_PER_RUN]

    if not pending_indexes:
        print("新しく検証する候補はありません。")
        return

    verified_history = load_json_list(VERIFIED_FILE)
    run_results = []

    for idx in pending_indexes:
        candidate = candidates[idx]

        print("")
        print("========================")
        print(
            "検証:",
            candidate.get("candidate_title")
            or candidate.get("title")
        )
        print("========================")

        sources, allowed_domains = find_official_sources(candidate)

        official_count = len([
            s for s in sources
            if s.get("source_type") == "official"
        ])

        print("取得ソース数:", len(sources))
        print("公式ソース数:", official_count)
        print("公式候補ドメイン:", allowed_domains)

        verification = verify_candidate(
            candidate,
            sources,
            allowed_domains,
        )

        if (
            official_count == 0
            and verification.get("status") == "verified"
        ):
            verification["status"] = "needs_manual"
            verification["recommended_action"] = "hold"
            verification["reason"] = (
                "公式・一次情報を自動取得できなかったため、"
                "verified判定を安全側でneeds_manualへ変更。 "
                + verification.get("reason", "")
            )

        record = {
            **candidate,
            "verification": verification,
            "official_domains_checked": allowed_domains,
            "sources_checked": [
                {
                    "url": s.get("url", ""),
                    "domain": s.get("domain", ""),
                    "source_type": s.get("source_type", ""),
                    "title": s.get("title", ""),
                }
                for s in sources
            ],
            "verified_at": now_jst.isoformat(),
        }

        candidates[idx]["status"] = verification["status"]
        candidates[idx]["verification"] = verification
        candidates[idx]["verified_at"] = now_jst.isoformat()

        verified_history.append(record)
        run_results.append(record)

    save_json_list(CANDIDATE_FILE, candidates)
    save_json_list(VERIFIED_FILE, verified_history)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report_path = REPORT_DIR / f"{today}.md"
    report_path.write_text(
        build_report(today, run_results),
        encoding="utf-8",
    )

    counts = {
        "verified": 0,
        "partial": 0,
        "rejected": 0,
        "needs_manual": 0,
    }

    for item in run_results:
        status = item["verification"].get(
            "status",
            "needs_manual",
        )
        counts[status] = counts.get(status, 0) + 1

    print("")
    print("========================")
    print("有料情報候補 自動検証完了")
    print("========================")
    print("検証件数:", len(run_results))
    print("verified:", counts.get("verified", 0))
    print("partial:", counts.get("partial", 0))
    print("needs_manual:", counts.get("needs_manual", 0))
    print("rejected:", counts.get("rejected", 0))
    print("保存:", VERIFIED_FILE)
    print("レポート:", report_path)


if __name__ == "__main__":
    main()
