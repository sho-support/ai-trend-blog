"""Short product names and literal specifications; no generated reviews."""
import re

def short_title(item):
    text=item.get('title') or item.get('display_title') or '商品情報'
    text=re.sub(r'【[^】]*(?:】|$)|＼[^／]*／|★[^★]*★',' ',text)
    text=re.sub(r'\s+',' ',re.split(r'[|｜]',text)[0]).strip()
    if not text:text=re.sub(r'[【】＼／★]','',item.get('title','商品情報'))
    return text[:32].rstrip()+'…' if len(text)>32 else text

def product_copy(item,edited):
    if item['id'] in edited:return edited[item['id']]
    title=item.get('title','')
    patterns=[r'\d+(?:\.\d+)?\s*(?:インチ|型|畳|GB|TB|mAh|mL|ml|kg|[gL])',r'\d+\s*(?:枚|個|袋|食|本|包)(?:入り|入|セット)?',r'\d{2,3}\s*Hz',r'\b(?:4K|8K|USB-C|Type-C|Bluetooth|IPS|有機EL|MiniLED)\b',r'個包装|無洗米|精米|防水|詰め替え|コードレス|折りたたみ']
    facts=[]
    for pattern in patterns:
        for m in re.findall(pattern,title,re.I):
            fact=re.sub(r'\s+','',m)
            if fact not in facts:facts.append(fact)
    desc='・'.join(facts[:3])
    return {'name':short_title(item),'headline':short_title(item),'description':desc+'。' if desc else '', 'features':[]}


def approved_a8(item, now=None):
    from datetime import datetime,timezone
    from urllib.parse import urlsplit
    try:
        u=urlsplit(item.get('url',''));site=urlsplit(item.get('site_url',''))
        expiry=datetime.fromisoformat(item.get('expires_at','').replace('Z','+00:00'))
        return (item.get('approved') is True and item.get('affiliate') is True
            and item.get('site_registered') is True and item.get('material_type')=='free_link'
            and bool(item.get('id')) and bool(item.get('title')) and bool(item.get('kind'))
            and expiry.tzinfo is not None and expiry>(now or datetime.now(timezone.utc))
            and u.scheme=='https' and not u.username and not u.password and u.hostname in ('px.a8.net','rpx.a8.net','ad.a8.net')
            and site.scheme=='https' and site.netloc=='sho-support.github.io'
            and (site.path=='/ai-trend-blog' or site.path.startswith('/ai-trend-blog/'))
            and (not item.get('image') or item.get('image_authorized') is True)
            and (item.get('price_yen') is None or type(item.get('price_yen')) in (int,float) and item['price_yen']>0))
    except (ValueError,TypeError,AttributeError):return False
