#!/usr/bin/env python3
"""Keep static portal cards and public metadata current without an LLM.

Only the pre-rendered card grid and updated-date text are regenerated.
Editorial data stays embedded in each page; expired cards remain as data for
audit but are not emitted as static markup or shown by client JS.
"""
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("deals/index.html", "events/index.html", "products/index.html")

def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)

def read_data(page):
    found = re.search(r'window\.PORTAL_DATA=(\{[\s\S]*?\});</script>', page)
    if not found:
        raise ValueError("Missing PORTAL_DATA")
    data = json.loads(found.group(1))
    if not isinstance(data.get("items"), list):
        raise ValueError("PORTAL_DATA.items must be a list")
    return data

def active(item, today):
    if not isinstance(item, dict):
        return False
    if item.get("end") and item["end"] < today:
        return False
    if item.get("expires_at"):
        try:
            dt = datetime.fromisoformat(item["expires_at"])
            if dt.tzinfo is None or dt <= datetime.now(JST):
                return False
        except (ValueError, TypeError):
            return False
    return True

def article_card(x, kind):
    area = "・".join(str(x.get(k) or "") for k in ("prefecture","place")).strip("・") if kind=="events" else str(x.get("shop") or "")
    date = (
        "開催: " + str(x.get("start") or "未記載") + ("〜" + str(x["end"]) if x.get("end") and x.get("end") != x.get("start") else "")
        if kind == "events" else "参照日 " + str(x.get("verified") or "未記載")
    )
    url = x.get("url") or ""
    if not isinstance(url, str) or not re.match(r"^https://", url):
        return ""
    return (
        '<article class="tile"><div class="tile-top"><div class="emblem">'
        + esc(x.get("icon", "✨"))
        + '</div></div><div class="tile-body"><div class="tile-tags">'
        + '<span class="tag highlight">' + esc(x.get("category")) + '</span>'
        + '<span class="tag">' + esc(area) + '</span></div>'
        + '<h3>' + esc(x.get("title")) + '</h3><p>' + esc(x.get("description")) + '</p>'
        + '</div><div class="tile-foot"><small>' + esc(date) + '</small>'
        + '<a class="go" href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">'
        + '公式情報を確認 ↗</a></div></article>'
    )

def regenerate(source, today):
    data = read_data(source)
    cards = "".join(article_card(x, data.get("kind")) for x in data["items"] if active(x, today))
    pattern = r'<div class="grid" id="cards">[\s\S]*?</div><div class="wide-note">'
    repl = '<div class="grid" id="cards">' + cards + '</div><div class="wide-note">'
    rendered, count = re.subn(pattern, lambda _: repl, source, count=1)
    if count != 1:
        raise ValueError("Card grid not found exactly once")
    rendered = re.sub(
        r'更新基準：\d{4}年\d{1,2}月\d{1,2}日',
        "更新基準：" + today[:4] + "年" + str(int(today[5:7])) + "月" + str(int(today[8:10])) + "日",
        rendered
    )
    return rendered

def main():
    today = datetime.now(JST).date().isoformat()
    for name in TARGETS:
        p = ROOT / name
        before = p.read_text(encoding="utf-8")
        after = regenerate(before, today)
        if before != after:
            p.write_text(after, encoding="utf-8")
            print("Updated:", name)
        else:
            print("No change:", name)

if __name__ == "__main__":
    main()
