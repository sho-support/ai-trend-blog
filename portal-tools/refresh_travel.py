#!/usr/bin/env python3
"""Rakuten Travel affiliate hotel discovery for cities with verified events.

No guessed event proximity, room availability or booking prices. Uses only the
official Rakuten Travel API, stores links with a short expiration and no keys.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

JST = timezone(timedelta(hours=9))
ENDPOINT = "https://openapi.rakuten.co.jp/engine/api/Travel/KeywordHotelSearch/20260731"
OUT = Path("portal-assets/travel-feed.json")
CITIES = [
    ("北海道", "札幌"),
    ("北海道", "帯広"),
    ("宮城県", "仙台"),
    ("青森県", "弘前"),
    ("東京都", "東京"),
    ("大阪府", "大阪"),
    ("京都府", "京都"),
    ("佐賀県", "佐賀"),
    ("大分県", "大分"),
]


def hotel_basics(value):
    """Support Rakuten's v1/v2 nested hotel containers without guessing fields."""
    if isinstance(value, list):
        for item in value:
            yield from hotel_basics(item)
    elif isinstance(value, dict):
        if "hotelBasicInfo" in value:
            block = value["hotelBasicInfo"]
            if isinstance(block, dict):
                yield block
        elif value.get("hotelName") and value.get("hotelInformationUrl"):
            yield value
        else:
            for key in ("hotel", "hotels"):
                if key in value:
                    yield from hotel_basics(value[key])


def main():
    app = os.getenv("RAKUTEN_APP_ID", "")
    key = os.getenv("RAKUTEN_ACCESS_KEY", "")
    affiliate = os.getenv("RAKUTEN_AFFILIATE_ID", "")
    if not all((app, key, affiliate)):
        print("楽天トラベルAPI認証情報が未設定。取得をスキップします。")
        return 0

    now = datetime.now(JST)
    results = []
    errors = 0
    for idx, (pref, city) in enumerate(CITIES):
        if idx:
            time.sleep(1.2)
        params = {
            "applicationId": app,
            "affiliateId": affiliate,
            "format": "json",
            "formatVersion": 2,
            "keyword": city,
            "hits": 5,
            "page": 1,
            "responseType": "middle",
        }
        req = Request(
            ENDPOINT + "?" + urlencode(params),
            headers={
                "accessKey": key,
                "Referer": "https://sho-support.github.io/ai-trend-blog/events/",
                "Origin": "https://sho-support.github.io",
                "User-Agent": "ShoEventDiscovery/1.0",
            },
        )
        try:
            with urlopen(req, timeout=22) as response:
                doc = json.load(response)
            if not isinstance(doc, dict) or doc.get("error"):
                raise ValueError("Invalid hotel API response")
            records = list(hotel_basics(doc.get("hotels", [])))
            count = 0
            for hotel in records:
                name = str(hotel.get("hotelName") or "").strip()
                hotel_id = str(hotel.get("hotelNo") or "")
                url = hotel.get("hotelInformationUrl") or ""
                parsed = urlsplit(url) if isinstance(url, str) else None
                if not (name and hotel_id and parsed and parsed.scheme == "https"):
                    continue
                if not (
                    parsed.hostname == "rakuten.co.jp"
                    or (parsed.hostname or "").endswith(".rakuten.co.jp")
                ):
                    continue
                results.append({
                    "id": f"travel-{city}-{hotel_id}",
                    "prefecture": pref,
                    "city": city,
                    "name": name[:90],
                    "url": url,
                    "affiliate": True,
                    "expires_at": (now + timedelta(hours=23)).isoformat(),
                })
                count += 1
                if count >= 3:
                    break
            print(f"宿泊施設: {city} API候補={len(records)} 表示可能={count}")
        except HTTPError as e:
            errors += 1
            print(f"::warning::楽天トラベルAPI: {city} HTTP={e.code}", file=sys.stderr)
            if e.code in (400, 401, 403, 429):
                break
        except Exception as e:
            errors += 1
            print(f"::warning::楽天トラベルAPI: {city} {type(e).__name__}", file=sys.stderr)

    if not results:
        print("ホテル情報0件。既存データは変更しません。")
        return 1 if errors else 0
    unique = list({x["id"]: x for x in results}.values())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({
            "updated_at": now.isoformat(),
            "source": ENDPOINT,
            "note": "PR・楽天トラベル公式API。宿泊日ごとの空き室・料金・会場からの距離は未確認。",
            "items": unique,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"宿泊候補保存：{len(unique)}件／APIエラー：{errors}件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
