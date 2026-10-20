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

JST = timezone(timedelta(hours=9))

NOTE_HISTORY_FILE = Path("note_draft_history.json")
PAID_HISTORY_FILE = Path("paid_note_draft_history.json")
PAID_CANDIDATE_FILE = Path("paid_info_candidates.json")

ARTICLE_DIR = Path("articles")
FREE_NOTE_DIR = Path("note_drafts")
PAID_NOTE_DIR = Path("paid_note_drafts")

REVIEW_PAID_ONLY = (
    os.environ.get("REVIEW_PAID_ONLY", "0").strip() == "1"
)

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY が設定されていません。")

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_content_with_fallback(contents, purpose):
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


def article_text(filename):
    path = ARTICLE_DIR / filename
    if not path.exists():
        return ""

    soup = BeautifulSoup(
        path.read_text(encoding="utf-8"),
        "html.parser",
    )
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    return re.sub(
        r"\s+",
        " ",
        soup.get_text(" ", strip=True),
    ).strip()


def clean_generated_text(text):
    return (
        (text or "")
        .replace("'''markdown", "")
        .replace("'''", "")
        .strip()
    )


def parse_json_object(text):
    text = clean_generated_text(text)
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise RuntimeError("レビューJSONを取得できませんでした。")
    return json.loads(match.group(0))


def build_paid_source_payload(candidate_keys):
    candidates = load_json_list(PAID_CANDIDATE_FILE)
    keyset = set(candidate_keys or [])
    payload = []

    for item in candidates:
        key = (
            item.get("url")
            or item.get("candidate_title")
            or item.get("title")
            or ""
        )
        if key not in keyset:
            continue

        verification = item.get("verification", {})

        payload.append(
            {
                "title": item.get("candidate_title") or item.get("title"),
                "status": item.get("status"),
                "urgency": item.get("urgency"),
                "safe_paid_title": verification.get("safe_paid_title"),
                "safe_summary": verification.get("safe_summary"),
                "verified_claims": verification.get("verified_claims", []),
                "missing_claims": verification.get("missing_claims", []),
                "contradictions": verification.get("contradictions", []),
                "recommended_action": verification.get("recommended_action"),
                "official_sources": [
                    {
                        "title": source.get("title", ""),
                        "url": source.get("url", ""),
                        "source_type": source.get("source_type", ""),
                    }
                    for source in item.get("sources_checked", [])
                    if source.get("source_type")
                    in {"official", "primary_release"}
                ],
            }
        )

    return payload


def review_pass(draft, source_material, note_type, pass_name):
    if pass_name == "facts":
        focus = """
【今回の重点】
・数字、金額、日付、曜日、期限、対象条件、型番、地域、提供条件が根拠と一致しているか
・購入期限と応募期限のように、意味の違う期限が混同されていないか
・未確認事項を確認済みのように書いていないか
・因果関係や条件を勝手に補っていないか
"""
    elif pass_name == "clarity":
        focus = """
【今回の重点】
・日本語として不自然、意味が取りづらい、主語が曖昧な箇所がないか
・無料部分と有料部分の役割が自然か
・無料部分だけでも概要は理解でき、有料部分には具体的な価値が残っているか
・同じ説明の重複、過度な煽り、回りくどい表現がないか
・期限や条件を読者が誤解しにくい順序で説明できているか
"""
    else:
        focus = """
【今回の重点】
・公開直前の最終校閲
・事実誤認、日付矛盾、数字矛盾、読者が誤解する表現が残っていないか
・タイトルと本文が一致しているか
・有料記事の場合、無料部分で重要な安全情報を隠していないか
・断定しすぎ、煽りすぎ、曖昧すぎのどれにも偏っていないか
"""

    prompt = f"""
あなたは日本語メディアの厳格な校閲・ファクトチェック担当です。

note種別:
{note_type}

以下の原稿を、与えた根拠資料だけを使って精査してください。
根拠にない情報を新しく足してはいけません。

{focus}

【必須ルール】
・問題がなくても必ず全文を読み直す
・修正が必要なら、意味を変えすぎず最小限で直す
・根拠資料にない数字、日付、条件を追加しない
・不明点は断定せず「未確認」とする
・Markdown構造を維持する
・有料noteの「# 🔒 ここから有料部分」は絶対に消さない
・URLは勝手に変更しない

JSONだけを返してください。

形式:
{{
  "result": "pass" または "rewrite",
  "issues": ["問題点1", "問題点2"],
  "revised_markdown": "修正後の全文。passの場合も元の全文をそのまま入れる"
}}

根拠資料:
{json.dumps(source_material, ensure_ascii=False, indent=2)}

原稿:
{draft}
"""

    response = generate_content_with_fallback(
        prompt,
        purpose=f"note校閲 {pass_name}",
    )

    result = parse_json_object(response.text)
    revised = (result.get("revised_markdown") or "").strip()

    if not revised:
        raise RuntimeError(f"{pass_name}レビュー後の原稿が空です。")

    issues = result.get("issues", [])
    print(f"{pass_name}レビュー結果:", result.get("result", "unknown"))
    if issues:
        for issue in issues:
            print("-", issue)
    else:
        print("- 指摘なし")

    return revised


def review_free_note(today):
    history = load_json_list(NOTE_HISTORY_FILE)
    todays = [
        item for item in history
        if item.get("draft_date_jst") == today
        and item.get("draft_filename")
        and item.get("article_filename")
    ]

    if not todays:
        print("本日レビューする無料note下書きはありません。")
        return

    record = todays[-1]
    draft_path = FREE_NOTE_DIR / record["draft_filename"]

    if not draft_path.exists():
        print("無料note下書きファイルが見つかりません:", draft_path)
        return

    draft = draft_path.read_text(encoding="utf-8")
    source = {
        "article_filename": record["article_filename"],
        "article_title": record.get("article_title", ""),
        "article_text": article_text(record["article_filename"])[:12000],
    }

    print("")
    print("===== 無料note 3段階レビュー =====")

    for pass_name in ["facts", "clarity", "final"]:
        draft = review_pass(
            draft,
            source,
            "無料note",
            pass_name,
        )

    draft_path.write_text(draft + "\n", encoding="utf-8")
    print("無料noteレビュー完了:", draft_path)


def review_paid_note(today):
    history = load_json_list(PAID_HISTORY_FILE)
    todays = [
        item for item in history
        if item.get("draft_date_jst") == today
        and item.get("draft_filename")
    ]

    if not todays:
        print("本日レビューする有料note下書きはありません。")
        return

    record = todays[-1]
    draft_path = PAID_NOTE_DIR / record["draft_filename"]

    if not draft_path.exists():
        print("有料note下書きファイルが見つかりません:", draft_path)
        return

    draft = draft_path.read_text(encoding="utf-8")
    source = {
        "candidate_keys": record.get("candidate_keys", []),
        "verified_candidates": build_paid_source_payload(
            record.get("candidate_keys", [])
        ),
    }

    if not source["verified_candidates"]:
        raise RuntimeError(
            "有料noteの根拠となるverified候補を復元できませんでした。"
        )

    print("")
    print("===== 有料note 3段階レビュー =====")

    for pass_name in ["facts", "clarity", "final"]:
        draft = review_pass(
            draft,
            source,
            "有料note",
            pass_name,
        )

    if "# 🔒 ここから有料部分" not in draft:
        raise RuntimeError(
            "レビュー後の有料noteから有料区切りが消えています。"
        )

    draft_path.write_text(draft + "\n", encoding="utf-8")
    print("有料noteレビュー完了:", draft_path)


def main():
    today = datetime.now(JST).date().isoformat()
    if not REVIEW_PAID_ONLY:
        review_free_note(today)

    review_paid_note(today)

    print("")
    print("========================")
    print("note多段階レビュー完了")
    print("========================")


if __name__ == "__main__":
    main()
