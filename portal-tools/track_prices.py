#!/usr/bin/env python3
"""Record actual Rakuten API price snapshots. No fabricated "sale" labels.

A "verified_deal" badge is only emitted if the same item has >= 3
distinct earlier observation dates in the last 30 days and the latest
observed price is at least 5% below the lowest earlier observed price.
This does NOT represent the Rakuten-wide lowest price.
"""
import json
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

JST=timezone(timedelta(hours=9))
ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"portal-assets"/"rakuten-feed.json"
HISTORY=ROOT/"portal-assets"/"price-history.json"

def main():
    now=datetime.now(JST)
    today=now.date()
    if not FEED.exists():
        raise SystemExit("Rakuten feed not found")
    feed=json.loads(FEED.read_text(encoding="utf-8"))
    if not isinstance(feed.get("items"),list) or not feed["items"]:
        raise SystemExit("Empty Rakuten feed: cannot record prices")
    data={"updated_at":None,"items":{}}
    if HISTORY.exists():
        existing=json.loads(HISTORY.read_text(encoding="utf-8"))
        if isinstance(existing.get("items"),dict):
            data=existing
    histories=data["items"]
    drops=0
    tracked=0
    date_floor=(today-timedelta(days=90)).isoformat()
    comparison_floor=(today-timedelta(days=30)).isoformat()
    for item in feed["items"]:
        item.pop("verified_deal",None)
        code=item.get("id")
        price=item.get("price_yen")
        if not isinstance(code,str) or not isinstance(price,int) or price<=0:
            continue
        current=histories.get(code,[])
        if not isinstance(current,list):current=[]
        records=[
            x for x in current
            if isinstance(x,dict) and isinstance(x.get("date"),str)
            and isinstance(x.get("price"),int) and x["price"]>0
            and date_floor<=x["date"]<today.isoformat()
        ]
        compare=[x for x in records if x["date"]>=comparison_floor]
        unique_prior_days=len(set(x["date"] for x in compare))
        if unique_prior_days>=3:
            prior_low=min(x["price"] for x in compare)
            percent=(prior_low-price)/prior_low*100
            if percent>=5:
                item["verified_deal"]={
                    "source":"当サイト観測の楽天API価格",
                    "previous_observed_low_yen":prior_low,
                    "current_yen":price,
                    "drop_percent":round(percent,1),
                    "comparison_days":unique_prior_days,
                    "observation_window_days":30,
                }
                drops+=1
        records.append({"date":today.isoformat(),"price":price})
        histories[code]=records
        tracked+=1
    # Clear old items/history without modifying today's feed when absent.
    for code in list(histories):
        records=histories.get(code,[])
        if not isinstance(records,list):
            histories.pop(code,None)
            continue
        histories[code]=[x for x in records
                         if isinstance(x,dict) and x.get("date","")>=date_floor]
        if not histories[code]: histories.pop(code,None)
    data["updated_at"]=now.isoformat()
    data["note"]="API経由の当サイト観測価格。楽天市場全体の最安値ではありません。送料・クーポン・ポイント・在庫未考慮。"
    HISTORY.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    FEED.write_text(json.dumps(feed,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"楽天観測価格記録：{tracked}件 / 厳格な値下がり判定：{drops}件 / 観測日数不足は表示なし")


if __name__=="__main__":
    main()
