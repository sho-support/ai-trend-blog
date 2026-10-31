#!/usr/bin/env python3
"""Build three independent commercial portals for Netlify from existing repo.

Netlify sets URL to the permanent site origin. No secrets or AI Trend Blog
article histories are published in the Netlify output.
"""
import html
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/"dist"
PORTAL_FOLDERS=("deals","events","products")
ASSET_FILES=("storefront.css","catalog.js","listing.js","product-copy.json","style.css","editorial.css","app.js","commerce.js","calculator.js","guide.js","travel.js","watch.js","rakuten-feed.json","travel-feed.json","price-history.json","a8-approved.json")
SOURCE_BASE="https://sho-support.github.io/ai-trend-blog"
target=os.getenv("URL","").rstrip("/")
if target and not target.startswith("https://"):
    raise SystemExit("Netlify URL must be HTTPS")
BASE=target or SOURCE_BASE

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
            if path.suffix.lower()==".html":
                body=body.replace(SOURCE_BASE+"/", BASE+"/")
            write(relative,body)
    for file in ASSET_FILES:
        shutil.copyfile(ROOT/"portal-assets"/file,DIST/"portal-assets"/file)

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
    write(Path("index.html"),content)

def make_sitemap():
    urls=["/","/deals/","/events/","/products/"]
    for p in (DIST/"deals").glob("*.html"):
        if p.name!="index.html":
            urls.append("/deals/"+p.name)
    for p in (DIST/"products").rglob("*.html"):
        if p.name!="index.html":
            urls.append("/"+p.relative_to(DIST).as_posix())
    root=ET.Element("urlset",{"xmlns":"http://www.sitemaps.org/schemas/sitemap/0.9"})
    for path in urls:
        rec=ET.SubElement(root,"url")
        ET.SubElement(rec,"loc").text=BASE+path
    write(Path("sitemap.xml"),ET.tostring(root,encoding="unicode"))
    write(Path("robots.txt"),"User-agent: *\nAllow: /\nSitemap: "+BASE+"/sitemap.xml\n")

def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST/"portal-assets").mkdir(parents=True)
    copy_pages()
    make_home()
    make_sitemap()
    write(Path("_headers"),"/portal-assets/*.json\n  Cache-Control: public, max-age=300\n")
    print("Netlify commercial static output:",DIST,"site",BASE)

if __name__=="__main__":
    main()
