#!/usr/bin/env python3
"""Build reviewed, short beginner guides without an LLM or external requests."""
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://sho-support.github.io/ai-trend-blog'
escape = html.escape


def render(guide, stamp):
    title = escape(guide['title']); description = escape(guide['description'], quote=True)
    url = BASE+'/articles/'+guide['slug']+'.html'
    steps = ''.join('<li>'+escape(x)+'</li>' for x in guide['steps'])
    sources = ''.join('<li><a href="'+escape(x['url'],quote=True)+'" target="_blank" rel="noopener noreferrer">'+escape(x['name'])+'</a></li>' for x in guide['sources'])
    example = ('<div class="example"><p class="sample-label">'+escape(guide['example_label'])+'</p><p>'+escape(guide['example'])+'</p></div>') if guide.get('example') else ''
    preview = '<div class="preview-steps">'+''.join('<span>'+escape(x)+'</span>' for x in guide['preview_steps'])+'</div>' if guide.get('preview_steps') else ''
    data = {'@context':'https://schema.org','@type':'Article','headline':guide['title'],
            'description':guide['description'],'datePublished':stamp,'dateModified':stamp,
            'mainEntityOfPage':url,'author':{'@type':'Organization','name':'AI Trend Blog'}}
    structured=json.dumps(data, ensure_ascii=False).replace('<','\\u003c')
    return f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | AI Trend Blog</title><meta name="description" content="{description}">
<meta name="robots" content="index,follow"><link rel="canonical" href="{url}">
<meta property="og:title" content="{title}"><meta property="og:description" content="{description}"><meta property="og:type" content="article"><meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary"><link rel="stylesheet" href="../editorial-assets/guides.css">
<script type="application/ld+json">{structured}</script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-J5ZDLF30CS"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','G-J5ZDLF30CS');</script>
<script defer src="../editorial-assets/guides.js"></script></head><body>
<header><a href="../index.html">AI Trend Blog</a></header><main><article>
<div class="eyebrow">はじめてのAI活用 · {stamp.replace('-','.')}</div>
<h1>{title}</h1><p class="lead">{escape(guide['lead'])}</p>{example}{preview}
<p class="cost">{escape(guide['cost'])}</p>
<h2>まずは試してみる</h2><ol>{steps}</ol>
<div class="prompt-box"><label for="ai-prompt">コピーして使えるお願い文</label>
<textarea id="ai-prompt" readonly>{escape(guide['prompt'])}</textarea>
<button type="button" data-copy-prompt="ai-prompt">お願い文をコピー</button><span role="status" aria-live="polite"></span></div>
<h2>使う前に、ここだけ確認</h2><p>{escape(guide['check'])}</p>
<div class="work"><h2>小さな仕事にするなら</h2><p>{escape(guide['work'])}</p></div>
<a class="start" href="https://chatgpt.com/" target="_blank" rel="noopener noreferrer">ChatGPTで試す ↗</a>
<details class="source"><summary>公式の説明・確認日</summary><ul>{sources}</ul><p>{stamp}確認。仕事への使い方は編集部の活用案です。</p></details>
</article><a class="back" href="../index.html#beginner-guides">← ほかの使い方を見る</a></main></body></html>'''


def build():
    packet=json.loads((ROOT/'editorial/beginner-guides.json').read_text())
    guides=packet['guides'];stamp=packet['checked_at']
    build_now=datetime.now(timezone(timedelta(hours=9))).isoformat()
    history_path=ROOT/'article_history.json';history=json.loads(history_path.read_text())
    cards=[]
    for guide in guides:
        filename=guide['slug']+'.html'
        (ROOT/'articles'/filename).write_text(render(guide,stamp),encoding='utf-8')
        row=next((x for x in history if x['filename']==filename),None)
        if row is None:
            row={'filename':filename,'created_at':build_now};history.append(row)
        row.update(title=guide['title'],source_title=guide['sources'][0]['name'],page_title=guide['sources'][0]['name'],
                   source_name='OpenAI',url=guide['sources'][0]['url'],editorial_kind='beginner_guide',
                   updated_at=build_now,social_copy=guide['social_copy'])
        cards.append(f'<a class="guide-card" href="articles/{filename}"><small>コピペで試せる · ChatGPT</small><h3>{escape(guide["title"])}</h3><p>{escape(guide["description"])}</p><span class="arrow">つくり方を見る →</span></a>')
    history_path.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n')
    path=ROOT/'index.html';soup=BeautifulSoup(path.read_text(),'html.parser')
    for old in soup.find_all('link',href='editorial-assets/guides.css'):old.decompose()
    if not soup.find('link',href='editorial-assets/home.css'):
        soup.head.append(soup.new_tag('link',rel='stylesheet',href='editorial-assets/home.css'))
    for old in soup.select('#beginner-guides'):old.decompose()
    section=BeautifulSoup('<section class="guide-discovery" id="beginner-guides"><h2>まずは、これをつくってみよう</h2><div class="guide-cards">'+''.join(cards)+'</div></section>','html.parser')
    soup.select_one('.hero').insert_after(section)
    soup.select_one('.hero h1').string='AIで、何をつくろう？'
    soup.select_one('.hero p').string='お店のSNS文、商品画像。コピーして試せる使い方から。'
    soup.select_one('.subtitle').string='はじめてのAI活用。つくって、仕事に生かす。'
    for card in soup.select('.article-card'):
        anchor=card.select_one('h2 a');p=card.find('p')
        if anchor and p:
            local=ROOT/anchor.get('href','')
            if local.is_file():
                content=BeautifulSoup(local.read_text(),'html.parser')
                first=content.select_one('article p')
                if first:
                    text=first.get_text(' ',strip=True)
                    sentence=re.split('(?<=。)',text)[0]
                    p.string=sentence if len(sentence)<=140 else text[:100].rstrip('、。')+'…'
    # The complete archive remains available; the home page stays short.
    for card in soup.select('.article-card')[6:]:card.decompose()
    listing=soup.select_one('.article-list')
    if listing and listing.parent.name!='details':
        title=listing.find_previous_sibling('h2')
        if title:title.decompose()
        details=soup.new_tag('details',attrs={'class':'archive-news'})
        listing.wrap(details)
        summary=soup.new_tag('summary');summary.string='これまでのニュースを読む';details.insert(0,summary)
    for box in soup.select('.side-box'):
        if box.h3 and box.h3.get_text(strip=True)=='今後追加予定':
            box.h3.string='使い方を試す';box.p.clear()
            for guide in guides:
                link=soup.new_tag('a',href='articles/'+guide['slug']+'.html');link.string=guide['title'];box.p.append(link);box.p.append(soup.new_tag('br'))
    for selector in ('meta[name="description"]','meta[property="og:description"]','meta[name="twitter:description"]'):
        tag=soup.select_one(selector)
        if tag:tag['content']='ChatGPTでSNS文や商品画像を作ってみよう。初心者がコピーして試せるお願い文と、仕事に生かすアイデアを紹介。'
    for selector in ('meta[property="og:title"]','meta[name="twitter:title"]'):
        tag=soup.select_one(selector)
        if tag:tag['content']='はじめてのAI活用 | AI Trend Blog'
    path.write_text(str(soup),encoding='utf-8')
    ns='http://www.sitemaps.org/schemas/sitemap/0.9';ET.register_namespace('',ns)
    path=ROOT/'articles-sitemap.xml';tree=ET.parse(path);root=tree.getroot()
    for guide in guides:
        url=BASE+'/articles/'+guide['slug']+'.html'
        element=next((e for e in root if e.findtext('{'+ns+'}loc')==url),None)
        if element is None:element=ET.SubElement(root,'{'+ns+'}url');ET.SubElement(element,'{'+ns+'}loc').text=url
        last=element.find('{'+ns+'}lastmod')
        if last is None:last=ET.SubElement(element,'{'+ns+'}lastmod')
        last.text=stamp
    ET.indent(tree);tree.write(path,encoding='utf-8',xml_declaration=True)
    print('Built',len(guides),'beginner guides; no external APIs called.')


if __name__=='__main__':build()
