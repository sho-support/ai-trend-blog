"""Render real catalogue content in HTML and maintain a crawlable URL inventory."""
import hashlib
import html
import json
from datetime import datetime, timezone
from urllib.parse import urlsplit, parse_qsl, urlencode

from product_text import approved_a8

BASE = 'https://sho-support.github.io/ai-trend-blog'
esc = lambda value: html.escape(str(value), quote=True)


def live(item, now=None):
    if item.get('source') == 'a8':
        return approved_a8(item, now)
    try:
        expiry = datetime.fromisoformat(item['expires_at'].replace('Z', '+00:00'))
        url = urlsplit(item['url'])
        return (expiry.tzinfo is not None and expiry > (now or datetime.now(timezone.utc))
                and item.get('approved') is True and item.get('affiliate') is True
                and type(item.get('price_yen')) in (int, float) and item['price_yen'] > 0
                and url.scheme == 'https' and not url.username and not url.password
                and (url.hostname == 'rakuten.co.jp' or url.hostname.endswith('.rakuten.co.jp')))
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


def share_image(url):
    parsed=urlsplit(url)
    query=dict(parse_qsl(parsed.query))
    if parsed.hostname=='thumbnail.image.rakuten.co.jp' and '_ex' in query:
        query['_ex']='600x600'
        return parsed._replace(query=urlencode(query)).geturl()
    return url


def image(item, copy, eager=False, large=False):
    url = item.get('image', '')
    if not url.startswith('https://'):
        return '<span class="photo-unavailable">商品写真は販売店で</span>'
    expanded=share_image(url)
    srcset=(' srcset="'+esc(url)+' 128w, '+esc(expanded)+' 600w" sizes="'
            + ('(max-width:600px) 90vw, 500px' if large else '(max-width:600px) 45vw, 300px')+'"') if expanded!=url else ''
    return ('<img class="product-image" src="' + esc(url) + '"'+srcset+' alt="' + esc(copy['name'])
            + '" width="600" height="600" decoding="async"'
            + (' fetchpriority="high"' if eager else ' loading="lazy"') + '>')


def price_text(price, copy):
    amount = format(price, ',')
    return amount + '円〜' if copy.get('price_from') is True else '¥' + amount


def unit_price(item):
    if item.get('id')=='rakuten-lifedrinkcompany-10000022' and isinstance(item.get('price_yen'),(int,float)):
        return '<p class="unit-price">約'+format(item['price_yen']/48,'.2f')+'円〜 / 本（48本・送料別）</p>'
    return ''


def rating(item):
    score=item.get('review_average');count=item.get('review_count')
    if item.get('source')!='rakuten' or not isinstance(score,(int,float)) or not 0<score<=5 or not isinstance(count,int) or count<=0:
        return ''
    return '<p class="review-summary"><span aria-hidden="true">★</span> '+format(score,'.2f')+' <small>/ 5・楽天市場 '+format(count,',')+'件</small></p><p class="review-date">'+esc(item.get('rating_verified') or item.get('verified',''))+'取得・販売ページ全体の評価</p>'


def card_notes(copy):
    lines=[]
    if copy.get('card_reason'):lines.append('<p class="card-reason"><span>選ぶ理由</span>'+esc(copy['card_reason'])+'</p>')
    if copy.get('card_caution'):lines.append('<p class="card-caution"><span>確認したい点</span>'+esc(copy['card_caution'])+'</p>')
    return ''.join(lines)


def cards(items, copies):
    rows = []
    for i, item in enumerate(items):
        copy = copies[item['id']]
        url = 'items/' + item['id'] + '.html'
        price = ('<p class="product-price">' + price_text(item['price_yen'], copy) + '</p>' + unit_price(item)
                 if item.get('price_yen') is not None else '')
        rows.append('<article class="product-card" data-kind="' + esc(item['kind']) + '">'
                    + '<a class="product-photo" href="' + url + '">' + image(item, copy, eager=i == 0) + '</a>'
                    + '<div class="product-card-body"><h2><a href="' + url + '">' + esc(copy['name']) + '</a></h2>'
                    + ('<p class="product-intro">' + esc(copy['description']) + '</p>' if copy['description'] else '')
                    + rating(item)+card_notes(copy)
                    + '<a class="guide-link" href="'+url+'">特徴・購入前の確認点を読む →</a>'
                    + '<div class="product-card-bottom">' + price
                    + '<a class="product-open product-buy" href="' + esc(item['url'])
                    + '" data-buy="' + esc(item['id']) + '" target="_blank" rel="noopener noreferrer sponsored" aria-label="'
                    + esc(copy['name']) + 'を' + ('公式ショップ' if item.get('source') == 'a8' else '楽天市場')
                    + 'で見る">' + ('公式ショップで見る' if item.get('source') == 'a8' else '楽天市場で見る')
                    + ' <span aria-hidden="true">↗</span></a></div></div></article>')
    return ('<p class="loading" id="catalog-status" role="status"' + (' hidden' if rows else '') + '>'
            + ('' if rows else '現在掲載できる商品はありません。') + '</p>'
            + '<div class="product-grid" id="catalog-grid">' + ''.join(rows) + '</div>')


def detail(item, copy):
    price = ('<p class="detail-price">' + price_text(item['price_yen'], copy) + '</p>' + unit_price(item)
             if item.get('price_yen') is not None else '')
    shop = item.get('seller') or item.get('shop') or '楽天市場'
    button = '公式ショップで価格を見る' if item.get('source') == 'a8' else '楽天市場で見る'
    return ('<div class="detail-photo">' + image(item, copy, eager=True, large=True) + '</div>'
            + '<div class="detail-info"><span class="ad-label">PR</span><h1>'
            + esc(copy.get('headline') or copy['name']) + '</h1>'
            + ('<p class="detail-intro">' + esc(copy['description']) + '</p>' if copy['description'] else '')
            + price + '<a class="buy-button" href="' + esc(item['url']) + '" data-buy="' + esc(item['id'])
            + '" target="_blank" rel="noopener noreferrer sponsored">' + button
            + ' <span aria-hidden="true">↗</span></a><p class="seller">' + esc(shop) + '</p></div>')


def breadcrumb(entries):
    return {'@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': name, 'item': BASE + '/' + path}
        for i, (name, path) in enumerate(entries)
    ]}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def inventory_entry(path, value, indexable=True):
    return {'url': BASE + '/' + path, 'fingerprint': fingerprint(value), 'indexable': indexable}
