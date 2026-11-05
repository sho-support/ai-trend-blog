#!/usr/bin/env python3
"""Record actual Rakuten API price snapshots. No fabricated "sale" labels.

A price at least 5% below the previous 30-day observed low can be
featured for three JST dates while daily observations confirm that price.
The reference price requires at least three earlier observation dates.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST=timezone(timedelta(hours=9))
ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"portal-assets"/"rakuten-feed.json"
HISTORY=ROOT/"portal-assets"/"price-history.json"
DEAL_DAYS=3


def observed_drop(records, day, price):
    """Return the original comparison for a recent, uninterrupted low price."""
    if not isinstance(records,list):
        return None
    prices={r['date']:r['price'] for r in records
            if isinstance(r,dict) and isinstance(r.get('date'),str)
            and type(r.get('price')) is int and r['price']>0}
    latest=max(prices,default='')
    if latest!=day.isoformat() or prices[latest]!=price:
        return None
    first_day=day
    for offset in range(1,DEAL_DAYS):
        earlier=day-timedelta(days=offset)
        if prices.get(earlier.isoformat())!=price:
            break
        first_day=earlier

    first_date=first_day.isoformat()
    floor=(first_day-timedelta(days=30)).isoformat()
    comparison={d:p for d,p in prices.items() if floor<=d<first_date}
    if len(comparison)<3:
        return None
    prior_low=min(comparison.values())
    if price*100>prior_low*95:
        return None
    return {
        'source':'当サイト観測の楽天API価格',
        'first_observed_date':first_date,
        'previous_observed_low_yen':prior_low,
        'previous_date':max(d for d,p in comparison.items() if p==prior_low),
        'current_yen':price,
        'drop_percent':round((prior_low-price)/prior_low*100,1),
        'comparison_days':len(comparison),
        'observation_window_days':30,
        'expires_at':(first_day+timedelta(days=DEAL_DAYS)).isoformat()+'T00:00:00+09:00',
    }


def main():
    if not FEED.exists():
        raise SystemExit("Rakuten feed not found")
    feed=json.loads(FEED.read_text(encoding="utf-8"))
    if not isinstance(feed.get("items"),list) or not feed["items"]:
        raise SystemExit("Empty Rakuten feed: cannot record prices")
    observed_at=datetime.fromisoformat(feed['updated_at'].replace('Z','+00:00'))
    if observed_at.tzinfo is None:
        raise SystemExit('Rakuten observation time has no timezone')
    today=observed_at.astimezone(JST).date()
    today_iso=today.isoformat()
    data={"updated_at":None,"items":{}}
    if HISTORY.exists():
        existing=json.loads(HISTORY.read_text(encoding="utf-8"))
        if isinstance(existing.get("items"),dict):
            data=existing
    histories=data["items"]
    drops=0
    tracked=0
    date_floor=(today-timedelta(days=90)).isoformat()
    for item in feed["items"]:
        item.pop("verified_deal",None)
        code=item.get("id")
        price=item.get("price_yen")
        if (item.get('verified')!=today_iso or not isinstance(code,str)
                or type(price) is not int or price<=0):
            continue
        current=histories.get(code,[])
        if not isinstance(current,list):current=[]
        records=[
            x for x in current
            if isinstance(x,dict) and isinstance(x.get("date"),str)
            and type(x.get("price")) is int and x["price"]>0
            and date_floor<=x["date"]
        ]
        if any(x['date']>today_iso for x in records):
            continue
        records=[x for x in records if x['date']!=today_iso]
        records.append({"date":today_iso,"price":price})
        deal=observed_drop(records,today,price)
        if deal:
            item['verified_deal']=deal
            drops+=1
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
    data["updated_at"]=observed_at.isoformat()
    data["note"]="API経由の当サイト観測価格。楽天市場全体の最安値ではありません。送料・クーポン・ポイント・在庫未考慮。"
    HISTORY.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    FEED.write_text(json.dumps(feed,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"楽天観測価格記録：{tracked}件 / 厳格な値下がり判定：{drops}件 / 観測日数不足は表示なし")


if __name__=="__main__":
    main()
