import os
import re
import json
import base64
from pathlib import Path

import requests


PRIVATE_REPO_TOKEN = os.environ.get(
    "PRIVATE_REPO_TOKEN"
)

PRIVATE_REPO_OWNER = "sho-support"
PRIVATE_REPO_NAME = "ai-trend-private"

LOCAL_DRAFT_DIR = Path(
    "paid_note_drafts"
)

PRIVATE_DRAFT_DIR = "paid_note_drafts"
PRIVATE_PACKAGE_DIR = "note_publish_packages"

GITHUB_API = "https://api.github.com"

PAID_MARKER = "# 🔒 ここから有料部分"


if not PRIVATE_REPO_TOKEN:
    raise RuntimeError(
        "PRIVATE_REPO_TOKEN が設定されていません。"
    )


HEADERS = {
    "Authorization": (
        f"Bearer {PRIVATE_REPO_TOKEN}"
    ),
    "Accept": (
        "application/vnd.github+json"
    ),
    "X-GitHub-Api-Version": (
        "2022-11-28"
    ),
}


def get_existing_file_sha(
    remote_path,
):
    url = (
        f"{GITHUB_API}/repos/"
        f"{PRIVATE_REPO_OWNER}/"
        f"{PRIVATE_REPO_NAME}/contents/"
        f"{remote_path}"
    )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    if response.status_code == 404:
        return None

    response.raise_for_status()

    data = response.json()

    return data.get(
        "sha"
    )


def upload_bytes(
    content,
    remote_path,
    commit_message,
):
    encoded = (
        base64
        .b64encode(content)
        .decode("ascii")
    )

    sha = get_existing_file_sha(
        remote_path
    )

    payload = {
        "message": commit_message,
        "content": encoded,
    }

    if sha:
        payload["sha"] = sha

    url = (
        f"{GITHUB_API}/repos/"
        f"{PRIVATE_REPO_OWNER}/"
        f"{PRIVATE_REPO_NAME}/contents/"
        f"{remote_path}"
    )

    response = requests.put(
        url,
        headers=HEADERS,
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    print(
        "Private Repoへ保存:",
        remote_path,
    )


def upload_text(
    text,
    remote_path,
    commit_message,
):
    upload_bytes(
        text.encode("utf-8"),
        remote_path,
        commit_message,
    )


def upload_file(
    local_path,
    remote_path,
):
    upload_bytes(
        local_path.read_bytes(),
        remote_path,
        "Update paid note draft",
    )


def extract_title(
    text,
    fallback,
):
    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("# "):
            title = (
                stripped[2:]
                .strip()
            )

            if title:
                return title

    return fallback


def remove_first_title(
    text,
):
    lines = text.splitlines()

    removed = False
    output = []

    for line in lines:
        if (
            not removed
            and line.strip().startswith("# ")
        ):
            removed = True
            continue

        output.append(line)

    return (
        "\n".join(output)
        .strip()
    )


def split_paid_content(
    text,
):
    if PAID_MARKER not in text:
        raise RuntimeError(
            "有料ラインの区切り "
            f"「{PAID_MARKER}」"
            "が原稿内にありません。"
        )

    before,
    after = text.split(
        PAID_MARKER,
        1,
    )

    free_body = (
        remove_first_title(
            before
        )
        .strip()
    )

    paid_body = (
        after
        .strip()
    )

    return (
        free_body,
        paid_body,
    )


def safe_folder_name(
    filename,
):
    stem = Path(
        filename
    ).stem

    stem = re.sub(
        r'[\\/:*?"<>|]+',
        "_",
        stem,
    )

    stem = re.sub(
        r"\s+",
        "_",
        stem,
    )

    return stem[:120]


def create_full_body(
    free_body,
    paid_body,
):
    return (
        free_body
        + "\n\n"
        + "【ここから有料部分】"
        + "\n\n"
        + paid_body
        + "\n"
    )


def create_posting_guide(
    title,
):
    return f"""# note投稿手順

タイトル:
{title}

1. title.txt の内容をnoteのタイトル欄へ貼る

2. free_part.txt を本文へ貼る

3. free_part.txt の末尾に
   noteの「有料エリア設定」を入れる

4. paid_part.txt を有料部分へ貼る

5. 表示崩れ・リンク・金額・期限を最終確認する

6. 販売価格を設定する

7. 公開する

注意:
この原稿は自動検証済み情報を元に作成されていますが、
公開直前にキャンペーン期限や条件が変わっていないか
最終確認してください。
"""


def create_metadata(
    draft_file,
    title,
    free_body,
    paid_body,
):
    return {
        "title": title,
        "source_draft": draft_file.name,
        "paid_marker": PAID_MARKER,
        "free_character_count": len(
            free_body
        ),
        "paid_character_count": len(
            paid_body
        ),
        "total_character_count": (
            len(free_body)
            + len(paid_body)
        ),
        "status": "ready_for_manual_note_post",
        "auto_publish": False,
    }


def upload_publish_package(
    draft_file,
    text,
):
    title = extract_title(
        text,
        draft_file.stem,
    )

    (
        free_body,
        paid_body,
    ) = split_paid_content(
        text
    )

    package_name = safe_folder_name(
        draft_file.name
    )

    base_path = (
        f"{PRIVATE_PACKAGE_DIR}/"
        f"{package_name}"
    )

    full_body = create_full_body(
        free_body,
        paid_body,
    )

    guide = create_posting_guide(
        title
    )

    metadata = create_metadata(
        draft_file,
        title,
        free_body,
        paid_body,
    )

    upload_text(
        title + "\n",
        f"{base_path}/title.txt",
        "Update note publish package",
    )

    upload_text(
        free_body + "\n",
        f"{base_path}/free_part.txt",
        "Update note publish package",
    )

    upload_text(
        paid_body + "\n",
        f"{base_path}/paid_part.txt",
        "Update note publish package",
    )

    upload_text(
        full_body,
        f"{base_path}/full_body.txt",
        "Update note publish package",
    )

    upload_text(
        guide,
        f"{base_path}/POSTING_GUIDE.md",
        "Update note publish package",
    )

    upload_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        f"{base_path}/metadata.json",
        "Update note publish package",
    )

    print("")
    print(
        "note投稿用パッケージ作成:"
    )
    print(
        base_path
    )
    print(
        "無料部分文字数:",
        len(free_body),
    )
    print(
        "有料部分文字数:",
        len(paid_body),
    )


def remove_local_file(
    path,
):
    path.unlink()

    print(
        "公開Repo側から削除予定:",
        path,
    )


def main():
    if not LOCAL_DRAFT_DIR.exists():
        print(
            "有料note原稿フォルダはありません。"
        )
        return

    draft_files = sorted(
        LOCAL_DRAFT_DIR.glob("*.md")
    )

    if not draft_files:
        print(
            "Private Repoへ送る"
            "有料note原稿はありません。"
        )
        return

    print(
        "Private Repoへ送る原稿数:",
        len(draft_files),
    )

    for draft_file in draft_files:
        text = draft_file.read_text(
            encoding="utf-8"
        )

        remote_path = (
            f"{PRIVATE_DRAFT_DIR}/"
            f"{draft_file.name}"
        )

        # 元の有料原稿をPrivateへ保存
        upload_file(
            draft_file,
            remote_path,
        )

        # note投稿用に分解したパッケージもPrivateへ保存
        upload_publish_package(
            draft_file,
            text,
        )

        # Privateへの保存成功後だけ公開Repo側から削除
        remove_local_file(
            draft_file
        )

    try:
        LOCAL_DRAFT_DIR.rmdir()
    except OSError:
        pass

    print("")
    print(
        "========================"
    )
    print(
        "有料note原稿のPrivate移送完了"
    )
    print(
        "note投稿用パッケージ生成完了"
    )
    print(
        "========================"
    )


if __name__ == "__main__":
    main()
