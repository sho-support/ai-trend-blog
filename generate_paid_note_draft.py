# generate_paid_note_draft.py

import os
import re
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from google import genai


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

MODEL_NAME = "gemini-3.8-flash"

FALLBACK_MODEL_NAMES = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
]

JST = timezone(
    timedelta(hours=9)
)

CANDIDATE_FILE = Path(
    "paid_info_candidates.json"
)

HISTORY_FILE = Path(
    "paid_note_draft_history.json"
)

DRAFT_DIR = Path(
    "paid_note_drafts"
)

MAX_ITEMS_PER_DRAFT = 5


if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY が設定されていません。"
    )


client = genai.Client(
    api_key=GEMINI_API_KEY
)


def generate_content_with_fallback(
    contents,
    purpose="Gemini生成",
):
    last_error = None

    for model_name in [
        MODEL_NAME,
        *FALLBACK_MODEL_NAMES,
    ]:
        try:
            print(
                f"{purpose}: "
                f"{model_name} を使用"
            )

            return (
                client.models.generate_content(
                    model=model_name,
                    contents=contents,
                )
            )

        except Exception as e:
            last_error = e

            print(
                f"{purpose}エラー "
                f"[{model_name}]: {e}"
            )

    raise RuntimeError(
        f"{purpose}失敗: "
        f"全モデルで生成できませんでした: "
        f"{last_error}"
    )


def load_json_list(path):
    if not path.exists():
        return []

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(
            value,
            list,
        ):
            return value

        return []

    except Exception:
        return []


def save_json_list(
    path,
    value,
):
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def safe_filename(text):
    text = re.sub(
        r'[\\/:*?"<>|]+',
        "_",
        text,
    )

    text = re.sub(
        r"\s+",
        "_",
        text,
    )

    text = text.strip(
        "._ "
    )

    return (
        text[:80]
        or "paid_note"
    )


def urgency_value(item):
    urgency = item.get(
        "urgency",
        "low",
    )

    values = {
        "high": 3,
        "medium": 2,
        "low": 1,
    }

    return values.get(
        urgency,
        0,
    )


def get_candidate_key(item):
    return (
        item.get("url")
        or item.get("candidate_title")
        or item.get("title")
        or ""
    )


def collect_verified_candidates(
    candidates,
    history,
):
    already_used = set()

    for record in history:
        for key in record.get(
            "candidate_keys",
            [],
        ):
            already_used.add(
                key
            )

    eligible = []

    for item in candidates:
        verification = item.get(
            "verification",
            {},
        )

        status = item.get(
            "status",
            verification.get(
                "status",
                "",
            ),
        )

        action = verification.get(
            "recommended_action",
            "",
        )

        key = get_candidate_key(
            item
        )

        if not key:
            continue

        if key in already_used:
            continue

        if status != "verified":
            continue

        if action != "publish_candidate":
            continue

        eligible.append(
            item
        )

    eligible.sort(
        key=lambda item: (
            urgency_value(item),
            int(
                item.get(
                    "score",
                    0,
                )
                or 0
            ),
            int(
                item.get(
                    "verification",
                    {},
                ).get(
                    "confidence",
                    0,
                )
                or 0
            ),
        ),
        reverse=True,
    )

    return eligible[
        :MAX_ITEMS_PER_DRAFT
    ]


def build_verified_payload(
    items,
):
    payload = []

    for item in items:
        verification = item.get(
            "verification",
            {},
        )

        sources = []

        for source in item.get(
            "sources_checked",
            [],
        ):
            if source.get(
                "source_type"
            ) not in {
                "official",
                "primary_release",
            }:
                continue

            sources.append(
                {
                    "url": source.get(
                        "url",
                        "",
                    ),
                    "title": source.get(
                        "title",
                        "",
                    ),
                    "source_type": source.get(
                        "source_type",
                        "",
                    ),
                }
            )

        payload.append(
            {
                "category":
                    item.get(
                        "category",
                        "",
                    ),

                "urgency":
                    item.get(
                        "urgency",
                        "",
                    ),

                "candidate_score":
                    item.get(
                        "score",
                        0,
                    ),

                "verification_confidence":
                    verification.get(
                        "confidence",
                        0,
                    ),

                "safe_paid_title":
                    verification.get(
                        "safe_paid_title",
                        "",
                    ),

                "safe_summary":
                    verification.get(
                        "safe_summary",
                        "",
                    ),

                "verified_claims":
                    verification.get(
                        "verified_claims",
                        [],
                    ),

                "missing_claims":
                    verification.get(
                        "missing_claims",
                        [],
                    ),

                "contradictions":
                    verification.get(
                        "contradictions",
                        [],
                    ),

                "official_sources":
                    sources,
            }
        )

    return payload


def create_paid_note(
    items,
):
    verified_payload = (
        build_verified_payload(
            items
        )
    )

    prompt = f"""
あなたは日本向けの有料noteを編集する
プロの情報編集者です。

以下は、
自動ファクトチェックを通過して
「verified / publish_candidate」
になった情報だけです。

このデータだけを根拠に、
有料note用の高品質な原稿を作成してください。

【最重要ルール】

・与えられていない事実を追加しない
・推測で価格、期限、条件を補わない
・「過去最安」「史上最高」「絶対お得」など、
  検証されていない表現は禁止
・verified_claims を最優先する
・missing_claims は未確認事項として明記する
・contradictions があれば隠さない
・公式URLを情報源として最後に掲載する
・二次情報だけを根拠に断定しない
・購入を煽りすぎない
・読者が自分で判断できる記事にする
・購入期限、応募期限、申請期限など意味の異なる日付は必ず役割を明示する
・複数の期限がある場合は「いつまでに何をするか」が一読で分かるように書く
・曜日は根拠データに含まれる場合のみ記載し、日付との矛盾を作らない
・「購入対象期間」と「応募期間」を混同しない

【このnoteの目的】

単なるニュース紹介ではなく、

「調べる時間を減らす」
「条件の見落としを防ぐ」
「期限や重要ポイントを整理する」
「得する可能性のある情報を判断しやすくする」

ことに価値を持たせてください。

【構成】

# タイトル

最初は無料公開部分です。

## 今回の優良情報

今回扱う内容を簡潔に紹介。

## こんな人向け

誰に価値がある情報なのか。

## 無料部分で分かること

重要ポイントを完全には出し切らず、
記事を読む価値が分かる程度に説明。

---

# 🔒 ここから有料部分

この見出しを必ずそのまま入れてください。

ここから先は購入者向けです。

各情報について、

## 1. 情報タイトル

### 結論

何が確認できたのか。

### 確認済みの内容

公式情報から確認できた内容を
具体的に整理。

### 金額・期限・条件

確認できているものだけ記載。
期限が複数ある場合は、最初に
「○月○日までに購入 → ○月○日までに応募」
のような1行要約を置いてから詳細を書く。

### 注意点

対象外条件、
応募条件、
未確認部分など。

### 誰に向いているか

確認済み事実から合理的に判断できる範囲。

### 今やるなら何を確認すべきか

読者が実際に行動する際の
チェック項目。

複数情報がある場合は
同じ形式で続けてください。

## 今回のまとめ

読者が判断しやすいよう整理。

## 情報源

公式または企業自身の一次発表URLを
箇条書きで掲載。

【文体】

・日本語
・です／ます調
・読みやすい
・煽りすぎない
・有料で読んでも損したと感じにくい密度
・具体的
・Markdown
・2,000〜4,000文字程度
・余計な挨拶不要
・ハッシュタグ不要

検証済みデータ:

{json.dumps(
    verified_payload,
    ensure_ascii=False,
    indent=2,
)}
"""

    response = (
        generate_content_with_fallback(
            prompt,
            purpose=(
                "有料note原稿生成"
            ),
        )
    )

    text = (
        response.text
        or ""
    ).strip()

    text = (
        text
        .replace(
            "```markdown",
            "",
        )
        .replace(
            "```",
            "",
        )
        .strip()
    )

    if not text:
        raise RuntimeError(
            "有料note原稿が空でした。"
        )

    return text


def main():
    now_jst = datetime.now(
        JST
    )

    today = (
        now_jst
        .date()
        .isoformat()
    )

    candidates = load_json_list(
        CANDIDATE_FILE
    )

    history = load_json_list(
        HISTORY_FILE
    )

    # 有料note原稿は1日1本まで。
    if any(
        item.get(
            "draft_date_jst"
        )
        == today
        for item in history
    ):
        print(
            "本日はすでに"
            "有料note原稿を生成済みです。"
        )

        return

    verified_items = (
        collect_verified_candidates(
            candidates,
            history,
        )
    )

    if not verified_items:
        print(
            "新しく有料note化できる"
            "verified候補はありません。"
        )

        return

    print(
        "有料note採用候補数:",
        len(
            verified_items
        ),
    )

    for item in verified_items:
        print(
            "-",
            item.get(
                "verification",
                {},
            ).get(
                "safe_paid_title",
                "",
            ),
        )

    draft = create_paid_note(
        verified_items
    )

    DRAFT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    first_title = (
        verified_items[0]
        .get(
            "verification",
            {},
        )
        .get(
            "safe_paid_title",
            "",
        )
        or
        verified_items[0]
        .get(
            "candidate_title",
            "",
        )
    )

    filename = (
        f"{today}_"
        f"{safe_filename(first_title)}"
        ".md"
    )

    path = (
        DRAFT_DIR
        / filename
    )

    path.write_text(
        draft + "\n",
        encoding="utf-8",
    )

    candidate_keys = [
        get_candidate_key(
            item
        )
        for item in verified_items
    ]

    history.append(
        {
            "draft_date_jst":
                today,

            "created_at":
                now_jst.isoformat(),

            "draft_filename":
                filename,

            "candidate_keys":
                candidate_keys,

            "candidate_count":
                len(
                    verified_items
                ),

            "status":
                "draft",

            "type":
                "paid_note",

            "auto_publish":
                False,
        }
    )

    save_json_list(
        HISTORY_FILE,
        history,
    )

    print("")
    print(
        "========================"
    )
    print(
        "有料note原稿生成成功"
    )
    print(
        "========================"
    )

    print(
        "保存先:",
        path,
    )

    print(
        "採用件数:",
        len(
            verified_items
        ),
    )

    print(
        "状態: draft"
    )

    print(
        "自動公開: OFF"
    )


if __name__ == "__main__":
    main()
