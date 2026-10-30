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
ASSET_FILES=("style.css","app.js","guide.js","travel.js","watch.js","rakuten-feed.json","travel-feed.json","price-history.json","a8-approved.json")
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
    title="トクサーチ・マチより・モノより｜お買い物・全国イベント・商品ガイド"
    panels=[
        ("⚡","トクサーチ","お菓子・家電・服・お米のお買い得情報を確認","deals/"),
        ("🎪","マチより","全国の開催日・地域・ジャンルからイベントを探す","events/"),
        ("🎁","モノより","商品比較とメーカー公式の仕様をチェック","products/"),
    ]
    cards="".join(
      '<a class="spot" href="'+link+'"><span class="big">'+icon+'</span>'
      '<b>'+html.escape(name)+'</b><span>'+html.escape(note)+'</span></a>'
      for icon,name,note,link in panels
    )
    content=(
      '<!doctype html><html lang="ja"><head><meta charset="utf-8">'
      '<meta name="viewport" content="width=device-width,initial-scale=1">'
      '<title>'+html.escape(title)+'</title>'
      '<meta name="description" content="買い物のお得情報・全国のイベント・商品比較をジャンル別に探せるポータル">'
      '<link rel="canonical" href="'+BASE+'/">'
      '<link rel="stylesheet" href="portal-assets/style.css"></head>'
      '<body><main class="shell"><div class="hero"><div class="tiny-label" style="color:#b8d4a2">SHO DISCOVERY NETWORK</div>'
      '<h1>暮らしの情報を、<em>もっと探しやすく。</em></h1>'
      '<p>公式情報を優先した、お買い得・おでかけ・商品選びの3サイト。</p></div>'
      '<div class="section-head"><div><h2>目的から探す</h2></div></div>'
      '<div class="spotlight">'+cards+'</div><div class="disclaimer"><strong>掲載と広告について</strong>'
      '各情報は参照時点の情報です。価格や開催日程は必ず公式リンクで再確認してください。'
      'アフィリエイト広告が入る場合はPR表示を行います。</div></main>'
      '<footer class="shell footer">© 2026 SHO DISCOVERY NETWORK</footer></body></html>'
    )
    write(Path("index.html"),content)

def make_sitemap():
    urls=["/","/deals/","/events/","/products/"]
    for p in (DIST/"deals").glob("*.html"):
        if p.name!="index.html":
            urls.append("/deals/"+p.name)
    for p in (DIST/"products").glob("*.html"):
        if p.name!="index.html":
            urls.append("/products/"+p.name)
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
