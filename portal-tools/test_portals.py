#!/usr/bin/env python3
"""Check storefront routes, category boundaries, public assets and feed safety."""
import ast
import importlib.util
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'portal-tools'))
from catalog_taxonomy import CATEGORIES, DEPARTMENTS, BY_KIND, eligible_title
from product_text import approved_a8, short_title, product_copy

class Page(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.refs=[];self.h1=0
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=='h1':self.h1+=1
        if 'id' in d:self.ids.append(d['id'])
        for key in ('src','href'):
            if key in d:self.refs.append(d[key])

def check(value,message):
    if not value:raise AssertionError(message)

def main():
    pages=[ROOT/'products/index.html',ROOT/'deals/index.html',ROOT/'events/index.html']
    pages+=list((ROOT/'products').rglob('*.html'))
    for path in set(pages):
        body=path.read_text(encoding='utf-8');page=Page();page.feed(body)
        check(page.h1==1,str(path)+' must have one h1')
        check(len(page.ids)==len(set(page.ids)),str(path)+' duplicate IDs')
        check('storefront.css' in body,str(path)+' not using compact storefront')
        check('Supported by Rakuten Developers</a>' in body,str(path)+' missing API attribution')
        for ref in page.refs:
            parsed=urlsplit(ref)
            if parsed.scheme or not parsed.path:continue
            target=(path.parent/parsed.path).resolve()
            check(target.exists(),str(path)+' broken link '+ref)
        check('unit-form' not in body and 'article-answer' not in body,str(path)+' old lecture/calculator restored')
    home=(ROOT/'products/index.html').read_text(encoding='utf-8')
    check('id="catalog-grid"' not in home,'home must not mix product listings')
    check(home.count('class="category-card"')==len(DEPARTMENTS),'home must show departments')
    check(len({c['key'] for c in CATEGORIES})==len(CATEGORIES),'duplicate shelf key')
    check(len({c['file'] for c in CATEGORIES})==len(CATEGORIES),'duplicate shelf route')
    for d in DEPARTMENTS:
        body=(ROOT/'products'/d['file']).read_text()
        check(body.count('class="category-card"')==len(d['children']),'department links must match its shelves')
        check('id="catalog-grid"' not in body,'department must not mix products')
    for title,kind,expected in [('仕事向け IPS 液晶ディスプレイ','monitor',True),('ゲーミングモニター 4K','monitor',False),('ゲーミングモニター 4K','gaming-monitor',True),('モニターアーム','gaming-monitor',False),('冷蔵庫 300L','refrigerators',True),('冷蔵庫用マット','refrigerators',False),('全自動洗濯機 8kg','washing-machines',True),('洗濯機用ホース','washing-machines',False),('Yoothi 互換品 液晶ディスプレイ 修理交換用液晶パネル','monitor',False),('プリンター用 イメージドラム 本体保証付','printers',False),('Nintendo Switch すぐに遊べるセット 純正アダプタ・ドック付き','game-software',False),('ジアイーノ 電極ユニット 空気清浄機 本体品番','air-purifiers',False),('グローブ スポーツウェア 手袋','sportswear',False),('カメラバッグ 三脚取付可','tripods',False),('ビデオカメラ 4k 8K 三脚 ビデオ カメラ 動画撮影 一眼レフ','tripods',False),('三脚 カメラ ビデオカメラ 一眼レフ','tripods',True)]:
        check(bool(eligible_title(title,kind))==expected,'classification error '+title)
    for c in CATEGORIES:
        body=(ROOT/'products'/c['file']).read_text(encoding='utf-8')
        check('"kind":"'+c['key']+'"' in body,c['key']+' missing category scope')
        check('id="catalog-grid"' in body,c['key']+' missing product grid')
        check('calculator.js' not in body,c['key']+' unwanted calculator')
    check('Nintendo Switch 2' in short_title({'title':'任天堂｜Nintendo Nintendo Switch 2 ゲーム機本体'}),'manufacturer separator hides product identity')
    check(short_title({'title':'限定150本 シチズン カンパノラ NZ0000-58L 高級ブランド 国産 メンズ腕時計'})=='限定150本 シチズン カンパノラ NZ0000-58L','a short product name must preserve its complete model and omit the clipped marketing word')
    watch={'id':'test-watch','kind':'wristwatches','title':'限定150本 シチズン カンパノラ NZ0000-58L'}
    check(not product_copy(watch,{})['description'],'model suffixes and edition counts must not become product specifications')
    laptop={'id':'test-laptop','kind':'laptops','title':'ノートパソコン メモリ8GB~32GB SSD128GB~1TB'}
    check(not product_copy(laptop,{})['description'],'a multi-variant title must not choose specifications for the displayed price')
    reviewed={'name':'シチズン カンパノラ NZ0000-58L','headline':'シチズン カンパノラ NZ0000-58L','description':'機械式の腕時計。','features':[]}
    check(product_copy(watch,{watch['id']:reviewed})==reviewed,'reviewed product copy must survive a feed rebuild')
    feed=json.loads((ROOT/'portal-assets/rakuten-feed.json').read_text())
    copies=json.loads((ROOT/'portal-assets/product-copy.json').read_text())
    keys={c['key'] for c in CATEGORIES};ids=set()
    for x in feed['items']:
        check(x.get('kind') in keys,'unclassified feed product')
        check(x.get('department')==BY_KIND[x['kind']]['department'],'wrong department')
        check(bool(eligible_title(x['title'],x['kind'])),'irrelevant product '+x['id'])
        check(x['id'] not in ids,'duplicate feed ID');ids.add(x['id'])
        check(x.get('approved') is True and x.get('affiliate') is True,'unapproved referral')
        u=urlsplit(x['url']);check(u.scheme=='https' and (u.hostname=='rakuten.co.jp' or u.hostname.endswith('.rakuten.co.jp')),'bad referral host')
        check(x.get('expires_at'),'missing expiry')
        check(isinstance(x.get('price_yen'),int) and x['price_yen']>0,'bad price')
        path=ROOT/'products/items'/(x['id']+'.html');check(path.exists(),'missing product detail '+x['id'])
        body=path.read_text();check('"id":"'+x['id']+'"' in body,'detail product identity mismatch')
        if x['id'] in copies:
            copy=copies[x['id']]
            check(len(copy['name'])<=45,'product name too long')
            check(len(copy['description'])<=80,'product introduction too long')
            check(len(copy['features'])<=3,'too many product features')
    a8=json.loads((ROOT/'portal-assets/a8-approved.json').read_text())
    a8_items=[x for x in a8.get('items',[]) if approved_a8(x)]
    for x in a8_items:
        check(x['id'] not in ids,'duplicate A8 product ID')
        check(x.get('kind') in keys,'unclassified A8 product')
        check(x.get('source')=='a8' and x.get('department')==BY_KIND[x['kind']]['department'],'wrong A8 source or department')
        check(x.get('seller')==x.get('shop'),'A8 seller must identify its own shop')
        check(x['id'] in copies,'missing A8 product copy')
        check(len(copies[x['id']]['description'])<=80,'A8 introduction too long')
        path=ROOT/'products/items'/(x['id']+'.html')
        check(path.exists() and '"id":"'+x['id']+'"' in path.read_text(),'missing or mismatched A8 detail')
    for name in ('storefront.css','catalog.js','listing.js','commerce.js','product-copy.json','catalog-taxonomy.json'):
        check((ROOT/'portal-assets'/name).is_file(),'missing public asset '+name)
    for script in ('catalog.js','listing.js','commerce.js'):
        subprocess.run(['node','--check',str(ROOT/'portal-assets'/script)],check=True)
    for name in ('build_storefront.py','catalog_taxonomy.py','product_text.py','storefront_seo.py','notify_indexnow.py','refresh_rakuten.py','build_guides.py','refresh_portals.py','build_commercial_site.py'):
        ast.parse((ROOT/'portal-tools'/name).read_text())
    subprocess.run(['node',str(ROOT/'portal-tools/test_commerce.js')],check=True)
    subprocess.run([sys.executable,str(ROOT/'portal-tools/test_discovery.py')],check=True)
    subprocess.run([sys.executable,str(ROOT/'portal-tools/test_feed_selection.py')],check=True)
    subprocess.run([sys.executable,str(ROOT/'portal-tools/test_sitemap_writers.py')],check=True)
    subprocess.run([sys.executable,str(ROOT/'portal-tools/test_article_quality.py')],check=True)
    subprocess.run([sys.executable,str(ROOT/'portal-tools/test_deal_news.py')],check=True)
    subprocess.run([sys.executable,str(ROOT/'portal-tools/test_black_friday.py')],check=True)
    subprocess.run([sys.executable,str(ROOT/'portal-tools/test_commercial_site.py')],check=True)
    print('PASS:',len(DEPARTMENTS),'departments,',len(CATEGORIES),'shelves,',len(ids),'Rakuten products,',len(a8_items),'A8 products, category boundaries and referral safety')

if __name__=='__main__':main()
