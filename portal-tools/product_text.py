"""Short product names and reviewed copy; no inferred specifications or reviews."""
import re

def short_title(item):
    text=(item.get('title') or item.get('display_title') or '商品情報').replace('\\','')
    text=re.sub(r'【[^】]*(?:】|$)|＼[^／]*／|★[^★]*★|≪[^≫]*≫|《[^》]*》|＜[^＞]*＞',' ',text)
    pieces=re.split(r'[|｜]',text)
    text=' '.join(pieces[:2]) if len(pieces)>1 and len(pieces[0].strip())<=12 else pieces[0]
    for pattern in [r'「[^」]*(?:楽天|ランキング|クーポン)[^」]*」',r'^\s*\d{1,2}/\d{1,2}[^★☆]*[★☆]',r'(?:楽天)?ランキング(?:第)?[\d,]+位(?:獲得|常連)?',r'楽天(?:第)?[\d,]+位',r'最大[\d,]+万?P当選',r'(?:限定)?(?:ポイント|P)\d+倍(?:で[\d,]+円)?',r'[\d,.]+[%％](?:OFF|オフ)(?:クーポン)?',r'(?:販売数|累計)[\d,]+万?(?:足|台|個)?突破[！!]*',r'送料無料[！!]*',r'「楽天で一番売れた\s*」']:
        text=re.sub(pattern,' ',text,flags=re.I)
    text=re.sub(r'[★☆⭐️◆◇◎※]+',' ',text)
    text=re.sub(r'\s+',' ',text).strip(' /！!')
    text=re.sub(r'^(?:(?:新品|三年保証|3年保証|\d年保証|\d{4}年最新モデル|最新モデル|正規品|公式店)\s*)+','',text).strip()
    if not text:text=re.sub(r'[【】＼／★]','',item.get('title','商品情報'))
    if len(text)>32:
        short=text[:32].rstrip()
        if re.search(r'[A-Za-z0-9]$',short) and re.match(r'[A-Za-z0-9]',text[32:]):
            space=short.rfind(' ')
            if space>=18:short=short[:space]
        return short+'…'
    return text


def product_copy(item,edited):
    if item['id'] in edited:return edited[item['id']]
    # Marketplace titles combine model codes, limited-edition counts and specs
    # from several variants. They do not establish the specs of the priced SKU.
    # Keep unreviewed listings photo/name/price only until copy is verified.
    name=short_title(item)
    return {'name':name,'headline':name,'description':'','features':[]}


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
