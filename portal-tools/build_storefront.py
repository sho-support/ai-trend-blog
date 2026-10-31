#!/usr/bin/env python3
"""Photo-first storefronts. Editorial copy stays short; no invented reviews."""
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://sho-support.github.io/ai-trend-blog'
JST = timezone(timedelta(hours=9))
CATEGORIES = [
    {'key':'snacks','name':'お菓子・スイーツ','file':'okashi-matome.html','icon':'🍪'},
    {'key':'rice','name':'お米','file':'okome-5kg.html','icon':'🍚'},
    {'key':'monitor','name':'モニター','file':'work-monitor.html','icon':'🖥️'},
    {'key':'power-bank','name':'モバイルバッテリー','file':'mobile-battery.html','icon':'🔋'},
    {'key':'laundry-detergent','name':'洗濯洗剤','file':'nichiyohin-matome.html','icon':'🧺'},
    {'key':'sneakers','name':'スニーカー','file':'sneakers.html','icon':'👟'},
    {'key':'skincare','name':'スキンケア','file':'skincare.html','icon':'🧴'},
    {'key':'pet-wipes','name':'ペット用品','file':'pet-supplies.html','icon':'🐾'},
]
E = lambda v: html.escape(str(v), quote=True)
JS = lambda v: json.dumps(v, ensure_ascii=False, separators=(',',':')).replace('<','\\u003c')
CREDIT = '''<!-- Rakuten Web Services Attribution Snippet FROM HERE -->
<a href="https://developers.rakuten.com/" target="_blank">Supported by Rakuten Developers</a>
<!-- Rakuten Web Services Attribution Snippet TO HERE -->'''


def header(brand, depth=1):
    prefix = '../' * depth
    brands = {'products':('モノより','◈'),'deals':('トクサーチ','↗'),'events':('マチより','◎')}
    name, mark = brands[brand]
    nav = ''.join(f'<a href="{prefix}{key}/"'+(' aria-current="page"' if key==brand else '')+f'>{value[0]}</a>' for key,value in brands.items())
    return f'<header class="site-header"><div class="header-inner"><a class="brand" href="{prefix}{brand}/"><span class="brand-mark" aria-hidden="true">{mark}</span>{name}</a><nav aria-label="サイト">{nav}</nav></div></header>'


def document(title, path, body, brand='products', depth=1, config=None, scripts=(), data=None):
    prefix = '../' * depth
    config_script = ''
    if config is not None:
        config_script = '<script>window.CATALOG_CONFIG='+JS(config)+';window.CATALOG_CATEGORIES='+JS(CATEGORIES)+';</script>'
    if data is not None:
        config_script += '<script>window.PORTAL_DATA='+JS(data)+';</script>'
    includes = ''.join(f'<script defer src="{prefix}portal-assets/{script}"></script>' for script in ('commerce.js',)+tuple(scripts))
    return f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(title)}。写真から商品やお出かけ先を探せます。">
<link rel="canonical" href="{BASE}/{path}"><meta property="og:title" content="{E(title)}"><meta property="og:url" content="{BASE}/{path}">
<meta property="og:type" content="website"><meta name="theme-color" content="#ffffff">
<link rel="stylesheet" href="{prefix}portal-assets/storefront.css">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-J5ZDLF30CS"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{if(!['localhost','127.0.0.1','terminal.local'].includes(location.hostname))dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','G-J5ZDLF30CS');</script>
</head><body><a class="skip-link" href="#main">本文へ</a>{header(brand,depth)}
<main id="main" class="page">{body}</main>
<footer class="site-footer"><div><a href="{prefix}deals/about.html">運営・広告方針</a><a href="{prefix}deals/privacy.html">プライバシー</a></div>
<p class="price-note">PR｜掲載価格は確認時点のものです。送料・在庫・購入条件は販売店でご確認ください。</p>
<div class="service-credit">{CREDIT}</div></footer>{config_script}{includes}</body></html>'''


def empty_cards():
    return '<p class="loading" id="catalog-status" role="status">商品を読み込み中…</p><div class="product-grid" id="catalog-grid"></div><noscript><p>商品写真の表示にはJavaScriptが必要です。</p></noscript>'


def category_links(selected='', subset=None):
    items = subset or CATEGORIES
    return '<nav class="category-nav" aria-label="商品ジャンル">'+''.join(
        f'<a href="{c["file"]}"'+(' aria-current="page"' if c['key']==selected else '')+f'>{c["name"]}</a>' for c in items
    )+'</nav>'


def write(relative, body):
    path = ROOT/relative
    # Only generated public HTML and the public copy dictionary are written.
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(body,encoding='utf-8')


def products():
    body = '<div class="page-heading"><h1>商品カテゴリー</h1><span class="ad-label">PR</span></div><div class="category-grid" id="category-grid">'
    body += ''.join(f'<a class="category-card" href="{c["file"]}" data-category="{c["key"]}"><div class="category-photo"><span aria-hidden="true">{c["icon"]}</span></div><h2>{c["name"]}<span aria-hidden="true">→</span></h2></a>' for c in CATEGORIES)
    body += '</div>'
    write('products/index.html', document('商品カテゴリー｜モノより','products/',body,config={'mode':'directory'},scripts=('catalog.js',)))
    for c in CATEGORIES:
        body = '<div class="breadcrumbs"><a href="./">カテゴリー</a><span aria-hidden="true">/</span><span>'+c['name']+'</span></div>'
        body += '<div class="page-heading"><h1>'+c['name']+'</h1><span class="ad-label">PR</span></div>'+category_links(c['key'])+empty_cards()
        write('products/'+c['file'],document(c['name']+'｜モノより','products/'+c['file'],body,config={'mode':'category','kind':c['key']},scripts=('catalog.js',)))
    subset=[c for c in CATEGORIES if c['key'] in ('power-bank','monitor')]
    body='<div class="page-heading"><h1>家電・デジタル</h1></div><div class="category-grid compact">'+''.join(f'<a class="category-card" href="{c["file"]}" data-category="{c["key"]}"><div class="category-photo"><span aria-hidden="true">{c["icon"]}</span></div><h2>{c["name"]}<span aria-hidden="true">→</span></h2></a>' for c in subset)+'</div>'
    write('products/mobile-battery-monitors.html',document('家電・デジタル｜モノより','products/mobile-battery-monitors.html',body,config={'mode':'directory'},scripts=('catalog.js',)))
    feed=json.loads((ROOT/'portal-assets/rakuten-feed.json').read_text())
    copies=json.loads((ROOT/'portal-tools/product_copy.json').read_text())
    known={c['key']:c for c in CATEGORIES}
    for item in feed.get('items',[]):
        key=item.get('kind');ident=item.get('id','')
        if key not in known or not re.fullmatch('[A-Za-z0-9_-]+',ident):continue
        c=known[key];copy=copies.get(ident,{})
        # No static API image or price: the browser checks the data's expiry first.
        title=copy.get('headline') or copy.get('name') or item.get('display_title') or item['title'][:45]
        body='<div class="breadcrumbs"><a href="../">カテゴリー</a><span aria-hidden="true">/</span><a href="../'+c['file']+'">'+c['name']+'</a></div>'
        body+='<article id="product-detail" class="product-detail"><div class="detail-photo placeholder" aria-label="商品写真を読み込み中"></div><div class="detail-info"><span class="ad-label">PR</span><h1>'+E(title)+'</h1><p class="loading" role="status">商品を読み込み中…</p></div></article>'
        body+='<div class="back-to-category"><a href="../'+c['file']+'">'+c['name']+'をもっと見る →</a></div>'
        write('products/items/'+ident+'.html',document(title+'｜モノより','products/items/'+ident+'.html',body,depth=2,config={'mode':'product','id':ident,'kind':key},scripts=('catalog.js',)))
    write('portal-assets/product-copy.json',json.dumps(copies,ensure_ascii=False,indent=2)+'\n')


def render_listing(data, today):
    cards=[]
    for x in data['items']:
        if x.get('end') and x['end']<today:continue
        if data['kind']=='events':
            start=x.get('start','');end=x.get('end','')
            date=start[5:].replace('-','/')+(' – '+end[5:].replace('-','/') if end and end!=start else '')
            place='・'.join(filter(None,[x.get('prefecture'),x.get('place')]))
            cards.append('<article class="event-card"><div class="event-date">'+E(date)+'</div><div><span class="event-category">'+E(x['category'])+'</span><h2><a href="'+E(x['url'])+'" target="_blank" rel="noopener noreferrer">'+E(x['title'])+'</a></h2><p class="event-place">'+E(place)+'</p></div><a class="text-link" href="'+E(x['url'])+'" target="_blank" rel="noopener noreferrer">詳細 →</a></article>')
        else:
            cards.append('<article class="offer-card"><span class="store-name">'+E(x.get('shop',''))+'</span><h2><a href="'+E(x['url'])+'" target="_blank" rel="noopener noreferrer">'+E(x['title'])+'</a></h2><p class="offer-label">'+E(x.get('label',''))+'</p><a class="text-link" href="'+E(x['url'])+'" target="_blank" rel="noopener noreferrer">公式サイトへ →</a></article>')
    return ''.join(cards)


def listings():
    data=json.loads((ROOT/'portal-tools/portal_content.json').read_text())
    today=datetime.now(JST).date().isoformat()
    for key in ('deals','events'):
        d=data[key]
        title='セール・クーポン' if key=='deals' else 'イベントを探す'
        filters='<div class="listing-filters" id="listing-filters"></div><div class="filter-chips" id="listing-chips"></div>'
        if key=='events':
            select='<a href="#listing-filters" class="text-link">地域・日付で絞る</a>'
        else:select='<a href="../products/" class="text-link">商品から探す →</a>'
        body='<div class="page-heading"><h1>'+title+'</h1>'+select+'</div>'+filters
        body+='<p id="listing-count" class="listing-count" role="status"></p><div id="listing-grid" class="'+('event-list' if key=='events' else 'offer-grid')+'">'+render_listing(d,today)+'</div>'
        if key=='events':
            body+='<section class="stay-section"><div class="page-heading"><h2>宿泊先も探す</h2><span class="ad-label">PR</span></div><p id="stay-status" class="small-text" role="status"></p><div id="event-stays" class="stay-grid"></div></section>'
        write(key+'/index.html',document(title+'｜'+('トクサーチ' if key=='deals' else 'マチより'),key+'/',body,brand=key,data=d,scripts=('listing.js',)))


def sitemap():
    path=ROOT/'site-sitemap.xml';ns='http://www.sitemaps.org/schemas/sitemap/0.9';ET.register_namespace('',ns)
    tree=ET.parse(path);root=tree.getroot();existing={x.findtext('{'+ns+'}loc') for x in root}
    for p in sorted((ROOT/'products').rglob('*.html')):
        url=BASE+'/'+str(p.relative_to(ROOT))
        if p.name=='index.html':url=url[:-10]
        if url not in existing:
            node=ET.SubElement(root,'{'+ns+'}url');ET.SubElement(node,'{'+ns+'}loc').text=url
            existing.add(url)
    tree.write(path,encoding='utf-8',xml_declaration=True)


def main():
    products();listings();sitemap()
    print('Storefronts built: separate categories, photo-first products, compact deals and events.')

if __name__=='__main__':main()
