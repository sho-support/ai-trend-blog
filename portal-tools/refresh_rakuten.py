#!/usr/bin/env python3
"""Refresh eligible Rakuten editorial product cards from the official 2026 API.

Requires GitHub Actions secrets: RAKUTEN_APP_ID, RAKUTEN_ACCESS_KEY.
Optional: RAKUTEN_AFFILIATE_ID. No token values enter the public output.
Offers are NOT labeled discounted or cheapest; prices are snapshots.
"""
import json
import re
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
OUT = Path("portal-assets/rakuten-feed.json")
JST = timezone(timedelta(hours=9))
from catalog_taxonomy import CATEGORIES, BY_DEPARTMENT, eligible_title
from product_text import short_title
SEARCHES=CATEGORIES

def shorten_title(title):
    return short_title({'title':title})


def main():
    app_id = os.getenv("RAKUTEN_APP_ID", "")
    access_key = os.getenv("RAKUTEN_ACCESS_KEY", "")
    affiliate_id = os.getenv("RAKUTEN_AFFILIATE_ID", "")
    if not app_id or not access_key:
        print("楽天のAPI設定なし。既存データを変更しません。")
        return 0
    now = datetime.now(JST)
    expires_at = (now + timedelta(hours=23)).isoformat()
    result = []
    used_codes = set()
    errors = 0
    coverage=[]
    for index, shelf in enumerate(SEARCHES):
        kind=shelf['key'];query=shelf['query'];dept=BY_DEPARTMENT[shelf['department']]
        cat=dept['name'];emoji=dept['icon']
        if index:
            time.sleep(1.1)  # Registration estimate: <= 1 request per second
        params = {
            "applicationId": app_id,
            "keyword": query,
            "format": "json",
            "formatVersion": 2,
            "hits": 15,
            "page": 1,
            "NGKeyword": "ふるさと納税",
            "availability": 1,
            "imageFlag": 1,
        }
        params['minPrice']=shelf['min_price']
        if shelf.get('genre_id'):params['genreId']=shelf['genre_id']
        if affiliate_id:
            params["affiliateId"] = affiliate_id
        req = Request(
            ENDPOINT + "?" + urlencode(params),
            headers={
                "accessKey": access_key,
                "User-Agent": "ShoCommercePortal/1.0",
                # Identifies our owned publishing site for Rakuten Web Application settings.
                "Referer": "https://sho-support.github.io/ai-trend-blog/deals/",
                "Origin": "https://sho-support.github.io",
            },
        )
        try:
            with urlopen(req, timeout=15) as response:
                payload = json.load(response)
            if not isinstance(payload, dict):
                raise ValueError("API response is not an object")
            if payload.get("error") or payload.get("errors"):
                raise ValueError("Rakuten API returned an error object")
            # Only report field names/counts in logs. Never print credentials,
            # item URLs, affiliate URLs or raw response bodies.
            safe_keys = [k for k in payload.keys() if k in (
                "items", "Items", "count", "hits", "page", "pageCount",
                "error", "errors", "data", "result", "status",
            )]
            objects = payload.get("items")
            if objects is None:
                objects = payload.get("Items")
            if objects is None and isinstance(payload.get("data"), dict):
                objects = payload["data"].get("items")
            if not isinstance(objects, list):
                print(
                    "API応答の形式不一致:",
                    "確認可能フィールド=", safe_keys,
                    "items型=", type(objects).__name__,
                    file=sys.stderr,
                )
                raise ValueError("API response contains no supported items list")
            if len(objects) == 0:
                print(
                    "API応答0件:",
                    "確認可能フィールド=", safe_keys,
                    "検索総件数=", payload.get("count") if isinstance(payload.get("count"), int) else "未提供",
                    file=sys.stderr,
                )
            kept = 0
            for v in objects:
                item = v.get("item", v) if isinstance(v, dict) else {}
                name = str(item.get("itemName") or "").strip()[:500]
                # A regular purchase guide must not silently recommend donations.
                if not eligible_title(name, kind):
                    continue
                # No ordinary product link is published as an affiliate link.
                link = item.get("affiliateUrl") if affiliate_id else item.get("itemUrl")
                if not name or not isinstance(link, str):
                    continue
                parsed = urlsplit(link)
                host = parsed.hostname or ""
                if parsed.scheme != "https" or parsed.username or parsed.password or not (host == "rakuten.co.jp" or host.endswith(".rakuten.co.jp")):
                    continue
                price = item.get("itemPrice")
                if not isinstance(price, int) or price <= 0:
                    continue
                code = str(item.get("itemCode") or "")
                if not code or code in used_codes:
                    continue
                image_list = item.get("mediumImageUrls") or []
                image = ""
                if image_list:
                    raw_image = image_list[0]
                    image = (raw_image.get("imageUrl") if isinstance(raw_image, dict) else raw_image) or ""
                    if not isinstance(image, str) or not image.startswith("https://"):
                        image = ""
                point_rate = item.get("pointRate")
                text = (
                    "楽天公式API取得時の参考価格: "
                    + f"{price:,}円。現在価格・送料・ポイント条件はリンク先で要確認。"
                )
                if isinstance(point_rate, (int, float)) and point_rate > 1:
                    text += f" API掲載ポイント倍率: {point_rate}倍。"
                # 楽天ウェブサービス規定に従い、価格表示の隣に注記。
                text += (
                    " このサイトで掲載されている情報は、トクサーチの作成者により運営されています。"
                    "価格、販売可能情報は、変更される場合があります。"
                    "購入時に楽天市場店舗（www.rakuten.co.jp）に表示されている価格が、"
                    "その商品の販売に適用されます。"
                )
                result.append({
                    "id": "rakuten-" + code.replace(":", "-"),
                    "category": cat,
                    "kind": kind,
                    "department": shelf["department"],
                    "source": "rakuten",
                    "shop": "楽天市場",
                    "icon": emoji,
                    "title": name,
                    "display_title": shorten_title(name),
                    "price_yen": price,
                    "seller": str(item.get("shopName") or "楽天市場出店ショップ")[:70],
                    "review_count": item.get("reviewCount") if isinstance(item.get("reviewCount"), int) else None,
                    "description": text,
                    "url": link,
                    "approved": True,
                    "verified": now.strftime("%Y-%m-%d"),
                    "expires_at": expires_at,
                    "affiliate": bool(affiliate_id),
                    "image": image,
                    "label": ("PR｜楽天公式API" if affiliate_id else "楽天公式API｜広告なし"),
                })
                used_codes.add(code)
                kept += 1
                if kept >= 3:
                    break
            coverage.append({'kind':kind,'name':shelf['name'],'count':kept,'status':'ok' if kept else 'empty'})
            print(f"候補: {cat} / {shelf['name']} API={len(objects)}件 掲載={kept}件")
        except HTTPError as e:
            errors += 1
            body = e.read(2048).decode("utf-8", errors="replace")
            # Print only recognized error codes; never expose credentials or URLs.
            known_errors = (
                "HTTP_REFERRER_NOT_ALLOWED",
                "HTTP_REFERRER_MISSING",
                "HTTP_ORIGIN_NOT_ALLOWED",
                "INVALID_ACCESS_KEY",
                "REQUESTED_SCOPES_NOT_ALLOWED",
                "wrong_parameter",
                "too_many_requests",
            )
            error_label = next((code for code in known_errors if code.lower() in body.lower()), "unknown")
            print(
                f"::error title=Rakuten API接続エラー::"
                f"カテゴリ={cat} HTTP={e.code} 理由={error_label}",
                file=sys.stderr,
            )
            if e.code in (400, 401, 403, 429):
                # An app-wide authorization or quota error affects all categories.
                # Do not make the same failing request eight times.
                break
        except Exception as e:
            errors += 1
            print(f"取得失敗: {cat} ({type(e).__name__})", file=sys.stderr)
    if not result:
        print("取得0件。古いデータを上書きしません。")
        return 1  # Never mark an empty feed as a successful connection test.
    output = {
        "updated_at": now.isoformat(),
        "source": ENDPOINT,
        "note": "楽天市場公式APIによる参考価格。最安値・値引き保証はありません。",
        "items": result,
        "coverage": coverage,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"更新: {len(result)}件 (失敗カテゴリ {errors})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
