import os
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

GITHUB_API = "https://api.github.com"


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


def upload_file(
    local_path,
    remote_path,
):
    content = (
        local_path
        .read_bytes()
    )

    encoded = (
        base64
        .b64encode(content)
        .decode("ascii")
    )

    sha = get_existing_file_sha(
        remote_path
    )

    payload = {
        "message": (
            "Update paid note draft"
        ),
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

    draft_files = list(
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
        remote_path = (
            f"{PRIVATE_DRAFT_DIR}/"
            f"{draft_file.name}"
        )

        upload_file(
            draft_file,
            remote_path,
        )

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
        "========================"
    )


if __name__ == "__main__":
    main()
