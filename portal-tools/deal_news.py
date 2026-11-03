"""Short product news from verified, still-current first-party price records."""
import html
import re
from datetime import datetime, timezone, timedelta

from storefront_seo import live, share_image
from product_text import short_title


def selected_deals(feed, history, copies, now=None):
    now=now or datetime.now(timezone.utc)
    rows=[]
    for item in feed.get('items',[]):
        if item.get('source')!='rakuten' or not live(item,now):continue
        day=item.get('verified','')
        if not isinstance(day,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):continue
        try:datetime.strptime(day,'%Y-%m-%d')
        except (TypeError,ValueError):continue
        low_day=(datetime.strptime(day,'%Y-%m-%d')-timedelta(days=30)).date().isoformat()
        records=[r for r in history.get('items',{}).get(item['id'],[])
                 if isinstance(r,dict) and isinstance(r.get('date'),str)
                 and low_day<=r['date']<day and type(r.get('price')) in (int,float) and r['price']>0]
        if len({r['date'] for r in records})<3:continue
        previous=min(r['price'] for r in records)
        deal=item.get('verified_deal') or {}
        if (item['price_yen']>=previous or deal.get('previous_observed_low_yen')!=previous
                or deal.get('current_yen')!=item['price_yen']):continue
        copy=copies.get(item['id'],{'name':short_title(item),'description':''})
        rows.append(dict(item,news_copy=copy,previous_price=previous,
                         previous_date=max(r['date'] for r in records if r['price']==previous)))
    rows.sort(key=lambda x:(x['price_yen']/x['previous_price'],x['id']))
    return rows[:12]


def render_deals(rows):
    escape=lambda x:html.escape(str(x),quote=True)
    out=[]
    for item in rows:
        copy=item['news_copy'];name=copy['name'];identity=escape(item['id']);url=escape(item['url'])
        attrs=f' href="{url}" data-deal-buy="{identity}" target="_blank" rel="noopener noreferrer sponsored"'
        photo=(f'<img src="{escape(share_image(item["image"]))}" alt="{escape(name)}" width="600" height="600" decoding="async" loading="lazy">'
               if item.get('image','').startswith('https://') else '<span>商品写真は販売店で</span>')
        out.append(f'<article class="deal-news-card"><a class="deal-news-photo"{attrs}>{photo}</a><div class="deal-news-body">'
                   f'<span class="ad-label">PR · 楽天市場</span><h2><a{attrs}>{escape(name)}、<span class="price-token">{item["price_yen"]:,}円〜</span></a></h2>'
                   f'<p class="deal-news-intro">{escape(copy.get("description",""))}</p>'
                   f'<p class="deal-news-before">{escape(item["previous_date"][5:].replace("-","/"))}記録：{item["previous_price"]:,}円</p>'
                   f'<a class="buy-button"{attrs}>楽天市場で見る ↗</a></div></article>')
    return ''.join(out) or '<p class="empty-results">現在、値下がりを確認できる商品はありません。</p>'
