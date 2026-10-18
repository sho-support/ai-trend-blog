import os
import sys
import json
import time
import subprocess
from pathlib import Path
from urllib.parse import quote

import requests
import markdown
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

OWNER = "sho-support"
PRIVATE_REPO = "ai-trend-private"
BRANCH = "main"
API_BASE = f"https://api.github.com/repos/{OWNER}/{PRIVATE_REPO}/contents"

PROFILE_DIR = Path.home() / ".ai-trend-note-browser"
NOTE_HOME = "https://note.com/"

MARKER_TEXT = "=== ここでNOTEの有料ラインを設定 ==="


def github_token():
    token = os.environ.get("NOTE_BOT_GITHUB_TOKEN", "").strip()
    if token:
        return token

    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
        )
        token = result.stdout.strip()
        if token:
            return token
    except Exception:
        pass

    raise RuntimeError(
        "Private Repoを読むための認証がありません。"
        " GitHub CLIでログインするか、"
        " NOTE_BOT_GITHUB_TOKEN を設定してください。"
    )


def headers():
    return {
        "Authorization": f"Bearer {github_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def api_get(path):
    url = f"{API_BASE}/{quote(path, safe='/')}"
    response = requests.get(
        url,
        headers=headers(),
        params={"ref": BRANCH},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def latest_package_path():
    items = api_get("note_publish_packages")
    folders = sorted(
        [
            item["path"]
            for item in items
            if item.get("type") == "dir"
        ]
    )
    if not folders:
        raise RuntimeError("note_publish_packages に記事がありません。")
    return folders[-1]


def file_text(path):
    item = api_get(path)
    download_url = item.get("download_url")
    if not download_url:
        raise RuntimeError(f"download_url がありません: {path}")

    response = requests.get(
        download_url,
        headers=headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def latest_package():
    base = latest_package_path()

    return {
        "base": base,
        "title": file_text(f"{base}/title.txt").strip(),
        "free": file_text(f"{base}/free_part.txt").strip(),
        "paid": file_text(f"{base}/paid_part.txt").strip(),
    }


def md_to_html(text):
    return markdown.markdown(
        text,
        extensions=[
            "extra",
            "sane_lists",
        ],
    )


def paste_rich_text(page, locator, html, plain):
    locator.click()
    page.evaluate(
        """async ({html, plain}) => {
            const item = new ClipboardItem({
                "text/html": new Blob([html], {type: "text/html"}),
                "text/plain": new Blob([plain], {type: "text/plain"}),
            });
            await navigator.clipboard.write([item]);
        }""",
        {"html": html, "plain": plain},
    )
    page.keyboard.press("Control+V")


def find_title(page):
    selectors = [
        'textarea[placeholder*="タイトル"]',
        'input[placeholder*="タイトル"]',
        '[contenteditable="true"][data-placeholder*="タイトル"]',
        '[contenteditable="true"][aria-label*="タイトル"]',
    ]

    for selector in selectors:
        locator = page.locator(selector).first
        if locator.count():
            try:
                locator.wait_for(state="visible", timeout=1500)
                return locator
            except Exception:
                pass

    raise RuntimeError(
        "noteのタイトル入力欄を見つけられませんでした。"
        " note側の画面変更の可能性があります。"
    )


def find_body(page, title_locator):
    candidates = page.locator('[contenteditable="true"]')

    visible = []
    for i in range(candidates.count()):
        item = candidates.nth(i)
        try:
            if item.is_visible():
                visible.append(item)
        except Exception:
            pass

    if not visible:
        raise RuntimeError("noteの本文入力欄を見つけられませんでした。")

    # 通常はタイトル以外の最後のcontenteditableが本文。
    return visible[-1]


def open_editor(page):
    page.goto(NOTE_HOME, wait_until="domcontentloaded")

    for label in ["投稿", "つくる"]:
        try:
            button = page.get_by_text(label, exact=True).first
            button.wait_for(state="visible", timeout=3000)
            button.click()
            page.wait_for_timeout(1500)
            return
        except Exception:
            pass

    # すでに投稿画面を開いているケースも許容。
    if page.locator('[contenteditable="true"]').count():
        return

    raise RuntimeError(
        "noteの投稿ボタンを見つけられませんでした。"
        " ログイン状態を確認してください。"
    )


def main():
    package = latest_package()

    print("対象:", package["base"])
    print("タイトル:", package["title"])

    full_md = (
        package["free"]
        + "\n\n"
        + MARKER_TEXT
        + "\n\n"
        + package["paid"]
    )

    full_html = (
        md_to_html(package["free"])
        + f"<p><strong>{MARKER_TEXT}</strong></p>"
        + md_to_html(package["paid"])
    )

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            permissions=[
                "clipboard-read",
                "clipboard-write",
            ],
            viewport={"width": 1400, "height": 900},
        )

        page = context.pages[0] if context.pages else context.new_page()

        try:
            open_editor(page)
        except Exception:
            print("")
            print("noteへのログインが必要なら、このブラウザでログインしてください。")
            print("ログイン後、noteトップまたは投稿画面を開いた状態でEnterを押してください。")
            input()
            open_editor(page)

        page.wait_for_timeout(1500)

        title = find_title(page)
        body = find_body(page, title)

        try:
            title.fill(package["title"])
        except Exception:
            title.click()
            page.keyboard.press("Control+A")
            page.keyboard.type(package["title"])

        paste_rich_text(
            page,
            body,
            full_html,
            full_md,
        )

        page.wait_for_timeout(2500)

        print("")
        print("noteへタイトル・本文を入力しました。")
        print("")
        print("次にブラウザ上で:")
        print("1. 「ここでNOTEの有料ラインを設定」の位置を確認")
        print("2. その位置にnoteの有料ラインを設定")
        print("3. 価格を確認")
        print("4. プレビュー")
        print("5. 問題なければ公開")
        print("")
        print("公開ボタンは安全のため自動では押しません。")

        input("確認が終わったらEnterでブラウザを閉じます: ")

        context.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("")
        print("ERROR:", e)
        input("Enterで終了: ")
        sys.exit(1)
