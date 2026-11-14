#!/usr/bin/env python3
"""Photo-first storefronts. Editorial copy stays short; no invented reviews."""
import html
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://sho-support.github.io/ai-trend-blog'
JST = timezone(timedelta(hours=9))
from catalog_taxonomy import DEPARTMENTS, CATEGORIES, BY_KIND, BY_DEPARTMENT, normalized_kind, public_category, eligible_title
from product_text import short_title, product_copy, approved_a8
from storefront_seo import live, image, cards, detail, breadcrumb, inventory_entry, fingerprint, share_image
from buying_guides import buying_guide
from deal_news import selected_deals, render_deals, point_offers, render_points
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


def document(title, path, body, brand='products', depth=1, config=None, scripts=(), data=None,
             description=None, image_url=None, noindex=False, initial=None, structured=()):
    prefix = '../' * depth
    config_script = ''
    if config is not None:
        lookup=CATEGORIES if config.get('mode')=='search' else BY_DEPARTMENT[BY_KIND[config['kind']]['department']]['children'] if config.get('kind') in BY_KIND else []
        config_script = '<script>window.CATALOG_CONFIG='+JS(config)+';window.CATALOG_CATEGORIES='+JS([public_category(c) for c in lookup])+';</script>'
    if data is not None:
        config_script += '<script>window.PORTAL_DATA='+JS(data)+';</script>'
    if initial is not None:
        config_script += '<script>window.CATALOG_INITIAL='+JS(initial)+';</script>'
    description=description or title.split('｜')[0]+'の掲載情報とリンク先を確認できます。'
    social='<meta property="og:site_name" content="'+{'products':'モノより','deals':'トクサーチ','events':'マチより'}[brand]+'"><meta property="og:locale" content="ja_JP">'
    social+='<meta property="og:description" content="'+E(description)+'"><meta name="twitter:description" content="'+E(description)+'"><meta name="twitter:title" content="'+E(title)+'">'
    if image_url and image_url.startswith('https://'):
        image_url=share_image(image_url)
        social+='<meta property="og:image" content="'+E(image_url)+'"><meta property="og:image:alt" content="'+E(title.split('｜')[0])+'"><meta name="twitter:card" content="summary_large_image">'
    else:social+='<meta name="twitter:card" content="summary">'
    webpage={'@type':'WebPage','@id':BASE+'/'+path,'url':BASE+'/'+path,'name':title,'description':description,'inLanguage':'ja'}
    schema='<script type="application/ld+json">'+JS({'@context':'https://schema.org','@graph':[webpage]+list(structured)})+'</script>'
    robots='<meta name="robots" content="noindex,follow">' if noindex else ''
    includes = ''.join(f'<script defer src="{prefix}portal-assets/{script}"></script>' for script in ('commerce.js',)+tuple(scripts))
    return f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(description)}">{robots}
<link rel="canonical" href="{BASE}/{path}"><meta property="og:title" content="{E(title)}"><meta property="og:url" content="{BASE}/{path}">
<meta property="og:type" content="website"><meta name="theme-color" content="#ffffff">{social}{schema}
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


def category_cards(rows, prefix='', items=(), copies=None):
    cards=[]
    for c in rows:
        is_department='children' in c
        attr='data-department' if is_department else 'data-category'
        icon=c.get('icon') or BY_DEPARTMENT[c['department']]['icon']
        matches=[x for x in items if x.get('department' if is_department else 'kind')==c['key']]
        photo=image(matches[0],copies[matches[0]['id']],eager=not cards) if matches else '<span aria-hidden="true">'+icon+'</span>'
        cards.append('<a class="category-card" href="'+prefix+c['file']+'" '+attr+'="'+c['key']+'"'+('' if matches else ' hidden')+'><div class="category-photo">'+photo+'</div><h2>'+E(c['name'])+'</h2></a>')
    return '<div class="category-grid" id="category-grid">'+''.join(cards)+'</div><p id="directory-status" class="loading" role="status"></p>'


def seed(items, copies):
    keys=('id','title','kind','department','category','source','image','url','price_yen','seller','shop',
          'review_average','review_count','rating_verified','verified','approved','affiliate','expires_at','site_registered','material_type','site_url','image_authorized')
    return {'items':[{k:x[k] for k in keys if k in x} for x in items],
            'copies':{x['id']:copies[x['id']] for x in items}}


def tile_seed(rows, items):
    found=[]
    for row in rows:
        key='department' if 'children' in row else 'kind'
        item=next((x for x in items if x.get(key)==row['key']),None)
        if item:found.append(item)
    return found


def search_form(prefix=''):
    return '<form class="catalog-search" action="'+prefix+'search.html" method="get" role="search"><input type="search" name="q" id="product-query" aria-label="商品検索" placeholder="商品名・ジャンルで探す"><button type="submit">検索</button></form>'


def products():
    feed_path=ROOT/'portal-assets/rakuten-feed.json'
    feed=json.loads(feed_path.read_text());changed=False
    previous=feed.get('items',[])
    feed['items']=[x for x in previous if eligible_title(x.get('title',''),normalized_kind(x))]
    changed=len(feed['items'])!=len(previous)
    for entry in feed.get('coverage',[]):
        count=sum(normalized_kind(x)==entry['kind'] for x in feed['items'])
        if entry['count']!=count:entry.update(count=count,status='ok' if count else 'empty');changed=True
    edited=json.loads((ROOT/'portal-tools/product_copy.json').read_text())
    copies=dict(edited)
    for item in feed.get('items',[]):
        kind=normalized_kind(item)
        if kind not in BY_KIND:continue
        dept=BY_DEPARTMENT[BY_KIND[kind]['department']]
        for k,v in {'kind':kind,'department':dept['key'],'category':dept['name'],'source':'rakuten'}.items():
            if item.get(k)!=v:item[k]=v;changed=True
        copies[item['id']]=product_copy(item,edited)
    if changed:feed_path.write_text(json.dumps(feed,ensure_ascii=False,indent=2)+'\n')
    items=list(feed.get('items',[]))
    a8=json.loads((ROOT/'portal-assets/a8-approved.json').read_text())
    a8_changed=False
    for item in a8.get('items',[]):
        if not approved_a8(item) or item.get('kind') not in BY_KIND:continue
        d=BY_DEPARTMENT[BY_KIND[item['kind']]['department']]
        for k,v in {'source':'a8','department':d['key'],'category':d['name']}.items():
            if item.get(k)!=v:item[k]=v;a8_changed=True
        items.append(item);copies[item['id']]=product_copy(item,edited)
    if a8_changed:write('portal-assets/a8-approved.json',json.dumps(a8,ensure_ascii=False,indent=2)+'\n')
    items=[x for x in items if live(x)]
    inventory=[]
    body='<div class="page-heading"><h2>カテゴリーから探す</h2><span class="ad-label">PR</span></div>'+search_form()+category_cards(DEPARTMENTS,items=items,copies=copies)
    picks=sorted(items,key=lambda x:x['id'] not in ('rakuten-lifedrinkcompany-10000022','rakuten-yokumoku-10000435','rakuten-anker-10001908'))[:10]
    hero_photo=image(picks[0],copies[picks[0]['id']],eager=True,large=True) if picks else ''
    hero='<section class="editorial-hero"><div><p class="eyebrow">MONOYORI / BUY BETTER</p><h1>買う前の「気になる」を、<br>選ぶ理由に。</h1><p>商品の特徴も、気をつけたいことも。<br>自分に合う買い物を、ここから。</p><div class="hero-actions"><a class="buy-button" href="#departments">ジャンルから探す ↓</a><a class="text-link" href="../deals/">お得情報を見る ↗</a></div></div><div class="hero-product">'+hero_photo+'<span>暮らしの定番を、じっくり選ぶ。</span></div></section>'
    picks_html='<section class="editorial-picks"><div class="section-heading"><div><p class="eyebrow">SHOPPING NOTES</p><h2>まずは、気になる商品から</h2></div><span class="ad-label">PR</span></div><p class="section-intro">食品・お菓子・モバイル用品。写真から商品を探せます。</p>'+cards(picks,copies).replace('catalog-grid','editorial-picks-grid').replace('catalog-status','editorial-picks-status')+'</section>' if picks else ''
    body=hero+picks_html+'<section id="departments">'+body+'</section>'
    photos=tile_seed(DEPARTMENTS,items)
    write('products/index.html',document('モノより｜家電・PC・食品をジャンルから探す','products/',body,config={'mode':'directory'},scripts=('catalog.js',),
        description='家電、PC、ゲーム、カメラ、食品、美容などをジャンル別に紹介。商品写真と短い紹介から、気になる商品と購入先を探せます。',
        image_url=photos[0].get('image') if photos else None,initial=seed(list({x['id']:x for x in photos+picks}.values()),copies)))
    inventory.append(inventory_entry('products/',[(x['id'],x.get('image')) for x in photos]))
    for d in DEPARTMENTS:
        selected=[x for x in items if x['department']==d['key']]
        photos=tile_seed(d['children'],selected)
        body='<div class="breadcrumbs"><a href="../">カテゴリー</a><span aria-hidden="true">/</span><span>'+d['name']+'</span></div>'
        body+='<div class="page-heading"><h1>'+d['name']+'</h1><span class="ad-label">PR</span></div>'+search_form('../')+category_cards(d['children'],'../',selected,copies)
        write('products/'+d['file'],document(d['name']+'｜モノより','products/'+d['file'],body,depth=2,config={'mode':'directory','department':d['key']},scripts=('catalog.js',),
            description=d['name']+'の商品を写真から探す。'+'、'.join(c['name'] for c in d['children'][:4])+'などをジャンル別に掲載。',
            image_url=photos[0].get('image') if photos else None,noindex=not selected,initial=seed(photos,copies),
            structured=[breadcrumb([('モノより','products/'),(d['name'],'products/'+d['file'])])]))
        inventory.append(inventory_entry('products/'+d['file'],[(x['id'],x.get('image')) for x in photos],bool(selected)))
        for c in d['children']:
            rows=[x for x in selected if x['kind']==c['key']]
            path='products/'+c['file']
            body='<div class="breadcrumbs"><a href="./">カテゴリー</a><span aria-hidden="true">/</span><a href="'+d['file']+'">'+d['name']+'</a><span aria-hidden="true">/</span><span>'+c['name']+'</span></div>'
            body+='<div class="page-heading"><h1>'+c['name']+'</h1><span class="ad-label">PR</span></div>'+category_links(c['key'],d['children'])+cards(rows,copies)
            schema=[breadcrumb([('モノより','products/'),(d['name'],'products/'+d['file']),(c['name'],path)])]
            if rows:schema.append({'@type':'ItemList','numberOfItems':len(rows),'itemListElement':[
                {'@type':'ListItem','position':i+1,'name':copies[x['id']]['name'],'url':BASE+'/products/items/'+x['id']+'.html'} for i,x in enumerate(rows)]})
            write(path,document(c['name']+'の商品｜モノより',path,body,config={'mode':'category','kind':c['key'],'department':d['key']},scripts=('catalog.js',),
                description=c['name']+'の商品写真・主な仕様・購入先を掲載。気になる商品を選んで、販売店の価格と条件を確認できます。',
                image_url=rows[0].get('image') if rows else None,noindex=not rows,initial=seed(rows,copies),structured=schema))
            inventory.append(inventory_entry(path,[(x['id'],copies[x['id']],x.get('image'),x.get('price_yen'),x.get('seller')) for x in rows],bool(rows)))
    body='<div class="breadcrumbs"><a href="./">カテゴリー</a><span aria-hidden="true">/</span><span>商品検索</span></div><div class="page-heading"><h1>商品を探す</h1><span class="ad-label">PR</span></div>'+search_form()+empty_cards()
    search_script='catalog.js?v='+hashlib.sha256((ROOT/'portal-assets/catalog.js').read_bytes()).hexdigest()[:12]
    write('products/search.html',document('商品検索｜モノより','products/search.html',body,config={'mode':'search'},scripts=(search_script,),noindex=True))
    subset=[BY_DEPARTMENT[k] for k in ('pc','gaming','mobile')]
    photos=tile_seed(subset,items)
    body='<div class="page-heading"><h1>PC・ゲーム・スマホ</h1></div>'+category_cards(subset,items=items,copies=copies)
    write('products/mobile-battery-monitors.html',document('PC・ゲーム・スマホ｜モノより','products/mobile-battery-monitors.html',body,config={'mode':'directory'},scripts=('catalog.js',),initial=seed(photos,copies)))
    inventory.append(inventory_entry('products/mobile-battery-monitors.html',[(x['id'],x.get('image')) for x in photos]))
    active_ids=set()
    for item in items:
        key=item.get('kind');ident=item.get('id','')
        if key not in BY_KIND or not re.fullmatch('[A-Za-z0-9_-]+',ident):continue
        c=BY_KIND[key];d=BY_DEPARTMENT[c['department']];copy=copies[ident]
        title=copy.get('headline') or copy['name']
        active_ids.add(ident);path='products/items/'+ident+'.html'
        body='<div class="breadcrumbs"><a href="../">カテゴリー</a><span aria-hidden="true">/</span><a href="../'+d['file']+'">'+d['name']+'</a><span aria-hidden="true">/</span><a href="../'+c['file']+'">'+c['name']+'</a></div>'
        body+='<article id="product-detail" class="product-detail">'+detail(item,copy)+'</article>'
        body+=buying_guide(ident,item)
        body+='<div class="back-to-category"><a href="../'+c['file']+'">'+c['name']+'をもっと見る →</a></div>'
        write(path,document((copy.get('seo_title') or copy['name'])+'｜モノより',path,body,depth=2,config={'mode':'product','id':ident,'kind':key,'department':d['key']},scripts=('catalog.js',),
            description=copy.get('seo_description') or copy['name']+'。'+(copy['description'] or c['name']+'の商品写真と購入先を掲載。'),
            image_url=item.get('image'),initial=seed([item],copies),
            structured=[breadcrumb([('モノより','products/'),(d['name'],'products/'+d['file']),(c['name'],'products/'+c['file']),(copy['name'],path)])]))
        semantic={k:item.get(k) for k in ('id','kind','image','url','price_yen','seller','shop','review_average','review_count','rating_verified')}
        inventory.append(inventory_entry(path,dict({'item':semantic,'copy':copy},**({'guide':buying_guide(ident,item)} if buying_guide(ident,item) else {}))))
    for old in (ROOT/'products/items').glob('*.html'):
        if old.stem in active_ids:continue
        match=re.search(r'window.CATALOG_CONFIG=(\{.*?\});',old.read_text())
        config=json.loads(match.group(1)) if match else {}
        c=BY_KIND.get(config.get('kind'))
        target='../'+c['file'] if c else '../'
        body='<article id="product-detail" class="product-detail"><div class="unavailable-product"><h1>この商品の掲載は終了しました</h1><p>同じジャンルの商品から探せます。</p><a class="buy-button secondary" href="'+target+'">'+(c['name'] if c else '商品一覧')+'を見る</a></div></article>'
        path='products/items/'+old.name
        write(path,document('掲載を終了した商品｜モノより',path,body,depth=2,noindex=True,
            config={'mode':'product','id':old.stem,'kind':config.get('kind'),'department':config.get('department')},scripts=('catalog.js',),initial=seed([],copies)))
        inventory.append(inventory_entry(path,{'status':'retired','kind':config.get('kind')},False))
    write('portal-assets/product-copy.json',json.dumps(copies,ensure_ascii=False,indent=2)+'\n')
    taxonomy={'departments':[{k:d[k] for k in ('key','name','file')} for d in DEPARTMENTS],'categories':[public_category(c) for c in CATEGORIES]}
    write('portal-assets/catalog-taxonomy.json',json.dumps(taxonomy,ensure_ascii=False,indent=2)+'\n')
    return inventory


def render_listing(data, today):
    cards=[]
    for x in data['items']:
        if x.get('end') and x['end']<today:continue
        if data['kind']=='events':
            start=x.get('start','');end=x.get('end','')
            date=start[5:].replace('-','/')+(' – '+end[5:].replace('-','/') if end and end!=start else '')
            place='・'.join(filter(None,[x.get('prefecture'),x.get('place')]))
            media=''
            if x.get('image_authorized') and x.get('image','').startswith('https://'):
                media='<figure class="listing-photo"><img src="'+E(x['image'])+'" alt="'+E(x['title'])+'の会場参考写真" loading="lazy"><figcaption>'+E(x.get('image_credit',''))+' <a href="'+E(x.get('image_source',''))+'">写真出典</a> <a href="'+E(x.get('image_license',''))+'">利用許諾</a></figcaption></figure>'
            cards.append('<article class="event-card">'+media+'<div class="event-date">'+E(date)+'</div><div><span class="event-category">'+E(x['category'])+'</span><h2><a href="'+E(x['url'])+'" target="_blank" rel="noopener noreferrer">'+E(x['title'])+'</a></h2><p class="event-place">'+E(place)+'</p><p class="event-description">'+E(x.get('description',''))+'</p></div><a class="text-link" href="'+E(x['url'])+'" target="_blank" rel="noopener noreferrer">詳細 →</a></article>')
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
        extra_scripts=('listing.js',)
        if key=='deals':
            feed=json.loads((ROOT/'portal-assets/rakuten-feed.json').read_text())
            history=json.loads((ROOT/'portal-assets/price-history.json').read_text())
            copies=json.loads((ROOT/'portal-tools/deal-copy.json').read_text())
            offers=selected_deals(feed,history,copies)
            checked=datetime.fromisoformat(feed['updated_at'].replace('Z','+00:00')).astimezone(JST)
            checked_label=f'{checked.month}/{checked.day} {checked:%H:%M}確認'
            options=''.join('<option value="'+E(x)+'">'+E(x)+'</option>' for x in sorted({x['category'] for x in offers}))
            body='<div class="page-heading"><h1>お得な商品</h1><a href="../products/" class="text-link">商品ジャンルから探す →</a></div><div class="deal-news-controls"><select id="deal-category" aria-label="商品ジャンル"><option value="all">すべてのジャンル</option>'+options+'</select><p id="deal-news-status" role="status">'+str(len(offers))+'件 · '+E(checked_label)+'</p></div><div class="deal-news-grid" id="deal-news-grid">'+render_deals(offers)+'</div><p class="deal-news-note">過去の金額は当サイトの掲載記録です。価格・送料・色や端子の選択は販売店でご確認ください。</p><section class="deal-campaigns"><h2>公式キャンペーン・クーポン</h2><p class="section-intro">こちらは公式案内への通常リンクです。このリンク自体の広告報酬は確認できていません。</p>'+filters+'<p id="listing-count" class="listing-count" role="status"></p><div id="listing-grid" class="offer-grid">'+render_listing(d,today)+'</div></section>'
            point_rows=point_offers(feed,copies)
            body='<section class="points-section"><div class="section-heading"><div><p class="eyebrow">POINT OFFERS</p><h2>ポイント倍率から探す</h2></div><span class="ad-label">PR</span></div><p class="section-intro">値下がりがない日も、ポイント条件を比較。倍率は取得時点の情報です。</p><div class="deal-news-grid" id="point-offers">'+render_points(point_rows)+'</div></section>'+body
            body+='<script>window.POINT_OFFERS_INITIAL='+JS(point_rows)+';</script>'
            body+='<script>window.DEAL_NEWS_INITIAL='+JS(offers)+';window.DEAL_NEWS_COPY='+JS(copies)+';window.DEAL_NEWS_UPDATED_AT='+JS(feed['updated_at'])+';</script>'
            body='<section class="listing-hero deals-hero"><p class="eyebrow">TOKUSEARCH / SMART SHOPPING</p><h2>お得は、条件まで見て選ぶ。</h2><p>値下がりの記録とポイント情報を分けて紹介。気になる商品の購入条件を比べられます。</p><a class="text-link" href="#point-offers">ポイント情報を見る ↓</a></section>'+body
            title='値下がり・ポイント・セール情報'
            extra_scripts=('listing.js','deal-news.js','point-offers.js')
        if key=='events':
            body='<section class="listing-hero"><p class="eyebrow">MACHIYORI / GO SOMEWHERE</p><h2>次の休日に、行きたい場所。</h2><p>季節の景色、街の催し。開催日と場所を確かめて、お出かけを計画しよう。</p></section>'+body
            body+='<section class="stay-section"><div class="page-heading"><h2>宿泊先も探す</h2><span class="ad-label">PR</span></div><p id="stay-status" class="small-text" role="status"></p><div id="event-stays" class="stay-grid"></div></section>'
        description=('値下がりを確認した商品を、写真・価格・短い紹介で掲載。ショップ別のセールやクーポンも探せます。' if key=='deals' else '開催日が確認できる地域のイベントを掲載。都道府県・日付・イベントの種類から、お出かけ先と公式案内を探せます。')
        page=document(title+'｜'+('トクサーチ' if key=='deals' else 'マチより'),key+'/',body,brand=key,data=d,scripts=extra_scripts,description=description)
        if key=='deals':page=page.replace('</head>','<link rel="stylesheet" href="../portal-assets/deal-news.css"></head>')
        write(key+'/index.html',page)


def sitemap(inventory):
    path=ROOT/'site-sitemap.xml';ns='http://www.sitemaps.org/schemas/sitemap/0.9';ET.register_namespace('',ns)
    tree=ET.parse(path);root=tree.getroot()
    for node in list(root):
        url=node.findtext('{'+ns+'}loc') or ''
        if url.startswith(BASE+'/products/'):root.remove(node)
    for file in ('deals/index.html','events/index.html','deals/about.html','deals/privacy.html'):
        url_path=file[:-10] if file.endswith('index.html') else file
        inventory.append(inventory_entry(url_path,(ROOT/file).read_text()))
    manifest_path=ROOT/'portal-assets/discovery-manifest.json'
    previous=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'pages':[]}
    previous={x['url']:x for x in previous['pages']}
    today=datetime.now(JST).date().isoformat()
    existing={x.findtext('{'+ns+'}loc') for x in root}
    for row in inventory:
        before=previous.get(row['url'],{})
        row['lastmod']=before.get('lastmod',today) if before.get('fingerprint')==row['fingerprint'] else today
        if not row['indexable']:continue
        if row['url'] not in existing:
            node=ET.SubElement(root,'{'+ns+'}url');ET.SubElement(node,'{'+ns+'}loc').text=row['url']
            ET.SubElement(node,'{'+ns+'}lastmod').text=row['lastmod'];existing.add(row['url'])
    old_content=path.read_bytes()
    tree.write(path,encoding='utf-8',xml_declaration=True)
    write('portal-assets/discovery-manifest.json',json.dumps({'version':1,'pages':sorted(inventory,key=lambda x:x['url'])},ensure_ascii=False,indent=2)+'\n')
    if path.read_bytes()!=old_content:
        index_path=ROOT/'sitemap-index.xml'
        index_tree=ET.parse(index_path)
        for entry in index_tree.getroot():
            if entry.findtext('{'+ns+'}loc')==BASE+'/site-sitemap.xml':
                stamp=entry.find('{'+ns+'}lastmod')
                if stamp is None:stamp=ET.SubElement(entry,'{'+ns+'}lastmod')
                stamp.text=today
        index_tree.write(index_path,encoding='utf-8',xml_declaration=True)


def main():
    inventory=products();listings();sitemap(inventory)
    print('Storefronts built: separate categories, photo-first products, compact deals and events.')

if __name__=='__main__':main()
