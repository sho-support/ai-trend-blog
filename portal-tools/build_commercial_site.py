#!/usr/bin/env python3
"""Build the three commercial portals, with an ad-free migration preview."""
import html
import os
import shutil
import xml.etree.ElementTree as ET
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from product_text import approved_a8

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/"dist"
PORTAL_FOLDERS=("deals","events","products")
ASSET_FILES=(
    "storefront.css","catalog-taxonomy.json","catalog.js","listing.js","deal-news.css","deal-news.js","black-friday.css",
    "product-copy.json","discovery-manifest.json","style.css","editorial.css","app.js","commerce.js",
    "calculator.js","guide.js","travel.js","watch.js","rakuten-feed.json","travel-feed.json",
    "price-history.json","a8-approved.json",
)
SOURCE_BASE="https://sho-support.github.io/ai-trend-blog"
target=(os.getenv("COMMERCIAL_SITE_URL") or os.getenv("URL","")).rstrip("/")
if target:
    parsed=urlsplit(target)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise SystemExit("Commercial site URL must be an HTTPS origin")
if os.getenv('CF_PAGES')=='1' and not target:
    raise SystemExit('Set COMMERCIAL_SITE_URL to the permanent Pages origin')
BASE=target or SOURCE_BASE
PREVIEW=os.getenv('COMMERCIAL_PREVIEW')=='1' or (BASE!=SOURCE_BASE and os.getenv('COMMERCIAL_MEDIA_APPROVED')!='1')
PAGES=os.getenv('CF_PAGES')=='1'

def public_url(url):
    if PAGES and url.startswith(BASE+'/'):
        return re.sub(r'(?:index)?\.html(?=[?#]|$)', '', url)
    return url

def rebase(body):
    # An A8 registration belongs to its reviewed media. Moving the site must
    # never manufacture a new approval by rewriting site_url in embedded data.
    saved=[]
    def keep(match):
        saved.append(match.group());return '__MEDIA_REGISTRATION_'+str(len(saved)-1)+'__'
    body=re.sub(r'"site_url"\s*:\s*"[^"\n]*"',keep,body)
    body=body.replace(SOURCE_BASE+'/',BASE+'/')
    if PAGES:
        body=re.sub(re.escape(BASE)+r'/[^\s<>"\']*',lambda m:public_url(m.group()),body)
    for i,value in enumerate(saved):body=body.replace('__MEDIA_REGISTRATION_'+str(i)+'__',value)
    return body

def preview_page(body):
    # Server-rendered photos and descriptions remain reviewable; preview
    # visits cannot send sales through an unregistered media or pollute GA4.
    body=re.sub(r'<script\b(?![^>]*type="application/ld\+json")[^>]*>.*?</script>','',body,flags=re.S|re.I)
    def disable(match):
        tag=match.group()
        if 'sponsored' in tag or re.search(r'https://(?:hb\.afl\.rakuten\.co\.jp|(?:r?px|ad)\.a8\.net|a\.r10\.to)/',tag):
            tag=re.sub(r'\bhref="[^"]*"','aria-disabled="true" tabindex="-1"',tag)
        return tag
    body=re.sub(r'<a\b[^>]*>',disable,body,flags=re.I)
    body=body.replace('</head>','<meta name="robots" content="noindex,follow"><style>[aria-disabled="true"]{opacity:.6;cursor:default}.migration-preview{padding:8px 16px;background:#eef1e9;text-align:center;font-size:12px}</style></head>')
    return body.replace('<body>','<body><p class="migration-preview">公開前の確認用</p>')

def check_media_scope():
    if PREVIEW or BASE==SOURCE_BASE:return
    offers=json.loads((ROOT/'portal-assets/a8-approved.json').read_text())
    if any(approved_a8(item) for item in offers.get('items',[])):
        raise SystemExit('Active A8 material still belongs to the old media; review the new media before production deployment')

def write(path,contents):
    target_path=DIST/path
    target_path.parent.mkdir(parents=True,exist_ok=True)
    target_path.write_text(contents,encoding="utf-8")

def copy_pages():
    for folder in PORTAL_FOLDERS:
        origin=ROOT/folder
        for path in origin.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in (".html",".css",".js",".json"):
                continue
            relative=path.relative_to(ROOT)
            body=path.read_text(encoding="utf-8")
            body=rebase(body)
            if PREVIEW and path.suffix.lower()=='.html':body=preview_page(body)
            write(relative,body)
    for file in ASSET_FILES:
        if PREVIEW and file.endswith(('.js','.json')):continue
        write(Path('portal-assets')/file,rebase((ROOT/'portal-assets'/file).read_text()))
    verification=json.loads((ROOT/'portal-tools/indexnow_config.json').read_text())
    filename=verification['key']+'.txt'
    shutil.copyfile(ROOT/filename,DIST/filename)

def make_home():
    title="商品・セール・イベントを探す"
    panels=[
        ("◈","モノより","商品をジャンルから探す","products/"),
        ("↗","トクサーチ","セール・クーポン","deals/"),
        ("◎","マチより","地域のイベント","events/"),
    ]
    cards="".join(
      '<a class="category-card" href="'+link+'"><div class="category-photo"><span aria-hidden="true">'+icon+'</span></div>'
      '<h2>'+html.escape(name)+'</h2><p style="padding:12px 15px;font-size:13px">'+html.escape(note)+'</p></a>'
      for icon,name,note,link in panels
    )
    content=(
      '<!doctype html><html lang="ja"><head><meta charset="utf-8">'
      '<meta name="viewport" content="width=device-width,initial-scale=1">'
      '<title>'+html.escape(title)+'</title>'
      '<meta name="description" content="買い物のお得情報・全国のイベント・商品比較をジャンル別に探せるポータル">'
      '<link rel="canonical" href="'+BASE+'/">'
      '<link rel="stylesheet" href="portal-assets/storefront.css"></head>'
      '<body><main class="page"><div class="page-heading"><h1>何を探しますか？</h1></div>'
      '<div class="category-grid">'+cards+'</div></main>'
      '<footer class="site-footer"><div><a href="deals/about.html">運営・広告方針</a><a href="deals/privacy.html">プライバシー</a></div>'
      '<p class="price-note">PR｜アフィリエイト広告を利用しています。</p></footer></body></html>'
    )
    write(Path("index.html"),preview_page(content) if PREVIEW else content)
    write(Path('404.html'),'<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,follow"><title>ページが見つかりません</title><h1>ページが見つかりません</h1><p><a href="/">トップページへ</a></p></html>')

def make_sitemap():
    if PREVIEW:
        write(Path('sitemap.xml'),'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>')
        write(Path('robots.txt'),'User-agent: *\nDisallow: /\n')
        return
    urls=["/","/deals/","/events/","/products/"]
    for p in (DIST/"deals").glob("*.html"):
        if p.name!="index.html" and 'content="noindex,follow"' not in p.read_text():
            urls.append("/deals/"+p.name)
    for p in (DIST/"products").rglob("*.html"):
        if p.name!="index.html" and 'content="noindex,follow"' not in p.read_text():
            urls.append("/"+p.relative_to(DIST).as_posix())
    root=ET.Element("urlset",{"xmlns":"http://www.sitemaps.org/schemas/sitemap/0.9"})
    for path in urls:
        rec=ET.SubElement(root,"url")
        ET.SubElement(rec,"loc").text=public_url(BASE+path)
    write(Path("sitemap.xml"),ET.tostring(root,encoding="unicode"))
    write(Path("robots.txt"),"User-agent: *\nAllow: /\nSitemap: "+BASE+"/sitemap.xml\n")

def main():
    check_media_scope()
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST/"portal-assets").mkdir(parents=True)
    copy_pages()
    make_home()
    make_sitemap()
    headers='/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n'
    if PREVIEW:headers+='  X-Robots-Tag: noindex, nofollow\n'
    headers+='/portal-assets/*.json\n  Cache-Control: public, max-age=300\n'
    write(Path('_headers'),headers)
    print('Commercial static output:',DIST,'site',BASE,'preview',PREVIEW)

if __name__=="__main__":
    main()
