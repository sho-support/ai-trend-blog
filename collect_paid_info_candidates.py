import os
import re
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

MODEL_NAME = "gemini-3.8-flash"
FALLBACK_MODEL_NAMES = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
]

JST = timezone(timedelta(hours=9))

CANDIDATE_FILE = Path("paid_info_candidates.json")
REPORT_DIR = Path("paid_info_candidates")
RUN_HISTORY_FILE = Path("paid_info_collection_history.json")

GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search"
    "?q={query}&hl=ja&gl=JP&ceid=JP:ja"
)

SEARCH_QUERIES = [
    ("お金が得", "Amazon セール 割引 キャンペーン"),
    ("お金が得", "楽天 セール ポイント キャンペーン"),
    ("お金が得", "家電 キャッシュバック キャンペーン"),
    ("お金が得", "カメラ キャッシュバック キャンペーン"),
    ("お金が得", "スマホ 通信 キャッシュバック キャンペーン"),
    ("お金が得", "旅行 ホテル クーポン キャンペーン"),
    ("お金が得", "サブスク 割引 キャンペーン"),
    ("お金が得", "ソフトウェア セール 永久ライセンス キャンペーン"),
    ("お金が得", "無料配布 ソフト アプリ キャンペーン"),
    ("お金を生む", "AI 副業 新サービス 収益化"),
    ("お金を生む", "生成AI 新サービス API 料金 プラン"),
    ("お金を生む", "クリエイター 収益化 新機能 キャンペーン"),
    ("時間を得する", "AI ツール 自動化 新機能"),
    ("時間を得する", "業務効率化 AI サービス 新機能"),
]

MAX_ITEMS_PER_QUERY = 5
RUN_SLOT = os.environ.get("PAID_RUN_SLOT", "primary").strip() or "primary"
MIN_SCORE_TO_KEEP = 85 if RUN_SLOT == "opportunity" else 70

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


def clean_text(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def collect_news_candidates():
    found = []
    seen_links = set()

    for category, query in SEARCH_QUERIES:
        url = GOOGLE_NEWS_RSS.format(query=quote_plus(query))
        print(f"検索: {query}")

        feed = feedparser.parse(url)

        for entry in feed.entries[:MAX_ITEMS_PER_QUERY]:
            link = getattr(entry, "link", "").strip()

            if not link or link in seen_links:
                continue

            seen_links.add(link)

            found.append(
                {
                    "category_hint": category,
                    "query": query,
                    "title": clean_text(getattr(entry, "title", "")),
                    "summary": clean_text(getattr(entry, "summary", "")),
                    "source": clean_text(
                        getattr(
                            getattr(entry, "source", {}),
                            "title",
                            "",
                        )
                        if hasattr(getattr(entry, "source", {}), "title")
                        else ""
                    ),
                    "url": link,
                    "published": clean_text(
                        getattr(entry, "published", "")
                    ),
                }
            )

    return found


def extract_json_array(text):
    text = (text or "").strip()
    text = text.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\[[\s\S]*\]", text)

    if not match:
        raise ValueError("Gemini応答からJSON配列を取得できませんでした。")

    return json.loads(match.group(0))


def score_candidates(raw_candidates):
    payload = json.dumps(
        raw_candidates,
        ensure_ascii=False,
        indent=2,
    )

    prompt = f"""
あなたは有料情報商品のリサーチ編集者です。

以下は日本向けニュース検索から集めた「候補」であり、
まだ事実確認前です。

目的は、将来の有料noteに載せる価値がある情報だけを
「商品候補箱」に残すことです。

有料情報の3分類:
1. お金が得
   - セール、値下げ、ポイント、キャッシュバック、無料配布など
2. お金を生む
   - AI副業、自動化、販売ネタ、新サービス、収益化機会など
3. 時間を得する
   - AIツール、自動化、業務効率化、テンプレ、時短機能など

【重要】
・ニュース見出しと要約だけで「過去最安」「史上最大」「確実に得」と断定しない
・価格、割引率、期限、対象条件、販売元は未確認なら未確認とする
・広告的な見出しだけでは高得点にしない
・一般的すぎるニュースは低得点にする
・有料読者が「知らないと損」「調べる手間が省ける」と感じるものを高得点にする
・緊急性、金銭メリット、希少性、実用性、検証可能性を評価する
・同じ話題の重複は1件に絞る

各候補について以下を返してください:
- source_index: 元配列の0始まりindex
- category: 「お金が得」「お金を生む」「時間を得する」のどれか
- score: 0〜100
- urgency: high / medium / low
- candidate_title: 有料情報候補として短く魅力的なタイトル
- why_paid_value: なぜ有料候補になるか
- verification_needed: 公開前に必ず確認する項目の配列
- reject_reason: 採用しない場合の理由。採用候補なら空文字

JSON配列だけを返してください。

候補:
{payload}
"""

    response = generate_content_with_fallback(
        prompt,
        purpose="有料情報候補の評価",
    )

    scored = extract_json_array(response.text)

    results = []

    for item in scored:
        try:
            idx = int(item.get("source_index"))
        except Exception:
            continue

        if idx < 0 or idx >= len(raw_candidates):
            continue

        base = raw_candidates[idx].copy()

        score = int(item.get("score", 0) or 0)

        base.update(
            {
                "category": item.get(
                    "category",
                    base.get("category_hint", "未分類"),
                ),
                "score": score,
                "urgency": item.get("urgency", "low"),
                "candidate_title": item.get(
                    "candidate_title",
                    base.get("title", ""),
                ),
                "why_paid_value": item.get(
                    "why_paid_value",
                    "",
                ),
                "verification_needed": item.get(
                    "verification_needed",
                    [],
                ),
                "reject_reason": item.get(
                    "reject_reason",
                    "",
                ),
            }
        )

        results.append(base)

    return results


def build_markdown_report(today, kept):
    lines = [
        f"# 有料情報候補箱 — {today}",
        "",
        "このファイルは自動収集した**未検証の候補**です。",
        "有料noteへ掲載する前に、価格・割引率・期限・対象条件・販売元などを必ず確認します。",
        "",
    ]

    if not kept:
        lines.append("本日はスコア基準を超える候補がありませんでした。")
        return "\n".join(lines) + "\n"

    kept_sorted = sorted(
        kept,
        key=lambda x: (
            x.get("score", 0),
            x.get("urgency") == "high",
        ),
        reverse=True,
    )

    for i, item in enumerate(kept_sorted, 1):
        lines.extend(
            [
                f"## {i}. {item.get('candidate_title') or item.get('title')}",
                "",
                f"- 分類: {item.get('category', '未分類')}",
                f"- スコア: {item.get('score', 0)}/100",
                f"- 緊急度: {item.get('urgency', 'low')}",
                f"- 元見出し: {item.get('title', '')}",
                f"- 情報源: {item.get('source', '') or 'Google News経由'}",
                f"- 公開日時: {item.get('published', '') or '不明'}",
                f"- URL: {item.get('url', '')}",
                f"- 有料候補にする理由: {item.get('why_paid_value', '')}",
                "",
                "### 公開前に確認すること",
            ]
        )

        verification = item.get("verification_needed") or []

        if isinstance(verification, list) and verification:
            for check in verification:
                lines.append(f"- {check}")
        else:
            lines.append("- 事実関係・条件・期限を公式情報で再確認")

        lines.append("")

    return "\n".join(lines) + "\n"


def main():
    now_jst = datetime.now(JST)
    today = now_jst.date().isoformat()

    run_history = load_json_list(RUN_HISTORY_FILE)

    if RUN_SLOT == "primary" and any(
        item.get("collection_date_jst") == today
        and item.get("run_slot", "primary") == "primary"
        for item in run_history
    ):
        print("本日の通常枠はすでに有料情報候補を収集済みです。")
        return

    raw_candidates = collect_news_candidates()

    print(f"収集候補数: {len(raw_candidates)}")

    if not raw_candidates:
        print("候補を取得できませんでした。")
        return

    scored = score_candidates(raw_candidates)

    kept = [
        item
        for item in scored
        if int(item.get("score", 0) or 0) >= MIN_SCORE_TO_KEEP
        and not item.get("reject_reason")
    ]

    existing = load_json_list(CANDIDATE_FILE)
    existing_urls = {
        item.get("url")
        for item in existing
        if item.get("url")
    }

    newly_added = []

    for item in kept:
        if item.get("url") in existing_urls:
            continue

        record = {
            **item,
            "collected_at": now_jst.isoformat(),
            "collection_date_jst": today,
            "status": "unverified",
            "product_type": "paid_note_candidate",
        }

        existing.append(record)
        newly_added.append(record)

    save_json_list(CANDIDATE_FILE, existing)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    suffix = now_jst.strftime("%H%M") if RUN_SLOT == "opportunity" else "primary"
    report_path = REPORT_DIR / f"{today}_{suffix}.md"
    report_path.write_text(
        build_markdown_report(today, newly_added),
        encoding="utf-8",
    )

    run_history.append(
        {
            "collection_date_jst": today,
            "run_slot": RUN_SLOT,
            "created_at": now_jst.isoformat(),
            "raw_count": len(raw_candidates),
            "scored_count": len(scored),
            "kept_count": len(kept),
            "new_count": len(newly_added),
        }
    )

    save_json_list(RUN_HISTORY_FILE, run_history)

    print("========================")
    print("有料情報候補箱 更新完了")
    print("========================")
    print("収集:", len(raw_candidates))
    print("基準通過:", len(kept))
    print("新規追加:", len(newly_added))
    print("保存:", CANDIDATE_FILE)
    print("日次レポート:", report_path)


if __name__ == "__main__":
    main()
