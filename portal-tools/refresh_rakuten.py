#!/usr/bin/env python3
"""Refresh eligible Rakuten editorial product cards from the official 2026 API.

Requires GitHub Actions secrets: RAKUTEN_APP_ID, RAKUTEN_ACCESS_KEY.
Optional: RAKUTEN_AFFILIATE_ID. No token values enter the public output.
Offers are NOT labeled discounted or cheapest; prices are snapshots.
"""
import json
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
SEARCHES = [
    ("食品・お菓子", "お菓子 詰め合わせ", "🍪"),
    ("お米・飲料", "米 5kg", "🍚"),
    ("家電・デジタル", "モバイルバッテリー USB-C", "🔋"),
    ("家電・デジタル", "モニター 4K", "🖥️"),
    ("日用品・生活", "洗剤 まとめ買い", "🧴"),
    ("ファッション", "スニーカー", "👟"),
    ("美容・コスメ", "スキンケア", "💄"),
    ("ペット", "ペット用品", "🐾"),
]
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
    errors = 0
    for index, (cat, query, emoji) in enumerate(SEARCHES):
        if index:
            time.sleep(1.1)  # Registration estimate: <= 1 request per second
        params = {
            "applicationId": app_id,
            "keyword": query,
            "format": "json",
            "formatVersion": 2,
            "hits": 3,
            "page": 1,
        }
        if affiliate_id:
            params["affiliateId"] = affiliate_id
        req = Request(
            ENDPOINT + "?" + urlencode(params),
            headers={
                "accessKey": access_key,
                "User-Agent": "ShoCommercePortal/1.0",
                # Identifies our owned publishing site for Rakuten Web Application settings.
                "Referer": "https://sho-support.github.io/ai-trend-blog/deals/",
            },
        )
        try:
            with urlopen(req, timeout=20) as response:
                payload = json.load(response)
            if not isinstance(payload, dict):
                raise ValueError("API response is not an object")
            if payload.get("error") or payload.get("errors"):
                raise ValueError("Rakuten API returned an error object")
            objects = payload.get("items", [])
            if not isinstance(objects, list):
                raise ValueError("API items is not a list")
            for v in objects:
                item = v.get("item", v) if isinstance(v, dict) else {}
                name = str(item.get("itemName") or "").strip()[:110]
                # No ordinary product link is published as an affiliate link.
                link = item.get("affiliateUrl") if affiliate_id else item.get("itemUrl")
                if not name or not isinstance(link, str) or urlsplit(link).scheme != "https":
                    continue
                price = item.get("itemPrice")
                if not isinstance(price, int) or price <= 0:
                    continue
                code = str(item.get("itemCode") or "")
                if not code:
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
                    "shop": "楽天市場",
                    "icon": emoji,
                    "title": name,
                    "description": text,
                    "url": link,
                    "approved": True,
                    "verified": now.strftime("%Y-%m-%d"),
                    "expires_at": expires_at,
                    "affiliate": bool(affiliate_id),
                    "image": image,
                    "label": ("PR｜楽天公式API" if affiliate_id else "楽天公式API｜広告なし"),
                })
            print(f"取得: {cat} {len(objects)}件")
        except HTTPError as e:
            errors += 1
            print(f"取得失敗: {cat} (HTTP {e.code})", file=sys.stderr)
        except Exception as e:
            errors += 1
            print(f"取得失敗: {cat} ({type(e).__name__})", file=sys.stderr)
    if not result:
        print("取得0件。古いデータを上書きしません。")
        return 1 if errors else 0
    output = {
        "updated_at": now.isoformat(),
        "source": ENDPOINT,
        "note": "楽天市場公式APIによる参考価格。最安値・値引き保証はありません。",
        "items": result,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"更新: {len(result)}件 (失敗カテゴリ {errors})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
