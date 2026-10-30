#!/usr/bin/env python3
"""Render maintained editorial guides; no paid API, network or invented reviews."""
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from guide_content import GUIDES, PUBLISHED

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://sho-support.github.io/ai-trend-blog"
BY_SLUG = {g["slug"]: g for g in GUIDES}
esc = lambda s: html.escape(str(s), quote=True)
CREDIT = '''<!-- Rakuten Web Services Attribution Snippet FROM HERE -->
<a href="https://developers.rakuten.com/" target="_blank">Supported by Rakuten Developers</a>
<!-- Rakuten Web Services Attribution Snippet TO HERE -->'''


def calculator(config):
    if not config:
        return ""
    cards = []
    for key, title in (("a", "候補A"), ("b", "候補B")):
        fields = [("price", "商品代（税込・円）", "", "1"),
                  ("shipping", "配送先への送料（円）", "0", "1"),
                  ("coupon", "購入時に引かれるクーポン（円）", "0", "1"),
                  ("quantity", config["label"], "", "any")]
        if config.get("dose"):
            fields.append(("dose", "同じ洗濯条件での1回分の量", "", "any"))
        inputs = "".join(
            f'<label for="calc-{key}-{name}">{esc(label)}'
            f'<input id="calc-{key}-{name}" name="{key}-{name}" type="number"'
            f' inputmode="decimal" min="0" step="{step}" value="{value}"'
            f' {"required" if name in ("price", "quantity", "dose") else ""}></label>'
            for name, label, value, step in fields
        )
        cards.append(f'<fieldset><legend>{title}</legend>{inputs}</fieldset>')
    data = json.dumps(config, ensure_ascii=False).replace("<", "\\u003c")
    return (
        '<section class="guide-calculator" id="unit-calculator" aria-labelledby="calc-heading">'
        '<div class="tiny-label accent">手元の価格で比べる</div>'
        '<h2 id="calc-heading">送料込みの単価を計算</h2>'
        '<p>購入画面の金額と届く量を入力してください。ポイント還元は計算に含めません。'
        '同じ種類・規格の商品を比べるための計算です。</p>'
        f'<form id="unit-form" data-config="{esc(data)}" novalidate>'
        '<div class="calculator-fields">' + "".join(cards) + '</div>'
        '<div class="calculator-actions"><button class="primary-action" type="submit">単価を比較する</button>'
        '<button type="button" id="calc-example">架空の例を入れる</button>'
        '<button type="reset">入力を消す</button></div>'
        '<p id="calc-mode" class="small-note"></p>'
        '<div id="calc-result" class="calculator-result" role="status" aria-live="polite">'
        '2つの候補を入力すると、単価と差額がここに表示されます。</div></form>'
        '<p class="small-note">計算式：（商品代＋送料−クーポン）÷合計量。' + ('さらに1回分の量を掛けます。' if config.get('dose') else '') +
        '入力した価格や数量は送信・保存しません。</p></section>'
    )


def page(g):
    url = BASE + "/products/" + g["slug"] + ".html"
    config = {k: g[k] for k in ("category", "kinds") if k in g}
    schema = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": g["title"], "description": g["description"],
        "datePublished": PUBLISHED, "dateModified": PUBLISHED,
        "mainEntityOfPage": url,
        "author": {"@type": "Organization", "name": "モノより"},
        "publisher": {"@type": "Organization", "name": "モノより"},
        "citation": [u for _, u in g["sources"]],
    }
    schema_json = json.dumps(schema, ensure_ascii=False).replace("<", "\\u003c")
    has_example = any("架空" in s["body"] for s in g["sections"])
    source_note = ('計算例は比較方法を説明する架空の条件です。' if has_example else '') + '商品の最新価格・規格・送料は購入先で確認してください。'
    toc = "".join(f'<li><a href="#{esc(s["id"])}">{esc(s["title"])}</a></li>' for s in g["sections"])
    if g.get("calculator"):
        toc += '<li><a href="#unit-calculator">送料込み単価を計算する</a></li>'
    sections = "".join(f'<section class="guide-section" id="{esc(s["id"])}">'
                       f'<h2>{esc(s["title"])}</h2>{s["body"]}</section>' for s in g["sections"])
    sources = "".join(f'<li><a href="{esc(u)}" target="_blank" rel="noopener noreferrer">'
                      f'{esc(label)} ↗</a></li>' for label, u in g["sources"])
    related = "".join(f'<a class="related-link" href="{slug}.html">{esc(BY_SLUG[slug]["icon"])} '
                      f'{esc(BY_SLUG[slug]["title"])} →</a>' for slug in g["related"])
    return f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(g['title'])}｜モノより</title><meta name="description" content="{esc(g['description'])}">
<meta name="theme-color" content="#172638"><link rel="canonical" href="{url}">
<meta property="og:type" content="article"><meta property="og:locale" content="ja_JP">
<meta property="og:title" content="{esc(g['title'])}"><meta property="og:description" content="{esc(g['description'])}">
<meta property="og:url" content="{url}"><meta property="og:site_name" content="モノより">
<meta name="twitter:card" content="summary">
<link rel="stylesheet" href="../portal-assets/style.css"><link rel="stylesheet" href="../portal-assets/editorial.css">
<script type="application/ld+json">{schema_json}</script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-J5ZDLF30CS"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{if(!['localhost','127.0.0.1','terminal.local'].includes(location.hostname))dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','G-J5ZDLF30CS');</script>
</head><body><a class="skip-link" href="#article">本文へ</a>
<header class="shell topbar"><a class="identity" href="./"><span class="mark">◈</span>モノより</a>
<nav class="topnav" aria-label="メイン"><a href="./">買い物ガイド</a><a href="../deals/">お買い得情報</a><a href="../events/">おでかけ</a></nav></header>
<main class="shell"><nav class="breadcrumbs" aria-label="パンくず"><a href="./">モノより</a><span aria-hidden="true">/</span><span>{esc(g['category'])}</span></nav>
<article class="editorial" id="article"><header class="article-header"><div class="article-meta"><span>{esc(g['icon'])} {esc(g['category'])}</span><span>編集日 {PUBLISHED.replace('-', '/')}</span><span>PRを含む</span></div>
<h1>{esc(g['title'])}</h1><p class="article-lead">{esc(g['lead'])}</p></header>
<div class="article-answer"><span class="tiny-label accent">選び方の出発点</span><p>{esc(g['answer'])}</p></div>
<ul class="buying-points">{''.join('<li>'+esc(s)+'</li>' for s in g['criteria'])}</ul>
<div class="article-actions"><a class="primary-action" href="#guide-cards">関連する商品を見る ↓</a>{'<a href="#unit-calculator">単価を計算する ↓</a>' if g.get('calculator') else ''}</div>
<p class="small-note"><strong>PR｜広告・アフィリエイトリンクを含みます。</strong>メーカーの案内と販売情報をもとに、購入時に比べたい条件を整理しています。</p>
<details class="article-toc"><summary>この記事で分かること</summary><ol>{toc}</ol></details>
{sections}{calculator(g.get('calculator'))}
<section class="article-sources" aria-labelledby="sources-title"><h2 id="sources-title">参照した公式情報</h2><ul>{sources}</ul><p>{source_note}</p></section>
</article>
<section class="guide-list" aria-labelledby="product-list-title"><div class="section-head"><div><div class="tiny-label accent">PR · 楽天市場</div><h2 id="product-list-title">このテーマに関連する商品</h2></div><a class="go" href="./#cards">ほかの商品を探す →</a></div>
<p id="guide-status" class="guide-status" aria-live="polite">商品情報を読み込み中です。</p><div class="grid" id="guide-cards"></div>
<noscript><p>商品一覧の表示にはJavaScriptが必要です。本文と計算方法はこのまま読めます。</p></noscript>
<p class="small-note">掲載価格は確認時の参考価格です。送料・選択した規格・クーポンによって支払額は変わります。23時間を過ぎた商品情報は表示しません。最安値の保証はありません。</p></section>
<section class="related-guides" aria-labelledby="related-title"><h2 id="related-title">こちらも読む</h2>{related}</section>
</main><footer class="shell footer"><span>© モノより</span><a href="./">買い物ガイドへ</a><span class="rakuten-credit">{CREDIT}</span><span class="policy-nav"><a href="../deals/about.html">運営・広告方針</a>　<a href="../deals/privacy.html">プライバシー</a></span></footer>
<script>window.GUIDE_CATEGORY={json.dumps(g['category'], ensure_ascii=False)};window.GUIDE_CONFIG={json.dumps(config, ensure_ascii=False)};</script>
<script defer src="../portal-assets/commerce.js"></script><script defer src="../portal-assets/guide.js"></script><script defer src="../portal-assets/calculator.js"></script>
</body></html>
'''


def update_index():
    path = ROOT / "products/index.html"
    source = path.read_text(encoding="utf-8")
    cards = "".join(f'<a class="spot" href="{g["slug"]}.html"><span class="big">{g["icon"]}</span>'
                    f'<b>{esc(g["title"])}</b><span>{esc(g["criteria"][0])}・{esc(g["criteria"][1])}</span></a>' for g in GUIDES)
    block = ('<section class="main" aria-labelledby="shopping-guides-title"><div class="section-head"><div>'
             '<div class="tiny-label accent">買う前に役立つガイド · PRを含む</div>'
             '<h2 id="shopping-guides-title">迷っていることから選ぶ</h2>'
             '<p>送料を入れるとどちらが安い？ 手持ちの機器に使える？ 購入前の疑問を具体的に整理。</p>'
             '</div><a class="go" href="#cards">商品候補を見る →</a></div><div class="spotlight">' + cards + '</div></section>')
    source, count = re.subn(r'<section class="main" aria-labelledby="shopping-guides-title">[\s\S]*?</section>', lambda _: block, source, count=1)
    if count != 1:
        raise ValueError("Guide section not found")
    match = re.search(r'window\.PORTAL_DATA=(\{[\s\S]*?\});</script>', source)
    if not match:
        raise ValueError("Product editorial data missing")
    data = json.loads(match.group(1))
    # Replace generic mall-homepage placeholders with maintained local guides.
    real_products = [item for item in data["items"] if item.get("id", "").startswith("real-")]
    guide_items = [{
        "id": "guide-" + g["slug"], "category": g["category"], "icon": g["icon"],
        "title": g["title"], "description": g["lead"], "shop": "モノよりのガイド",
        "url": BASE + "/products/" + g["slug"] + ".html",
        "guide_path": g["slug"] + ".html", "label": "買い物ガイド",
        "verified": PUBLISHED,
    } for g in GUIDES]
    for item in real_products:
        if item.get("category") == "お菓子・食品":
            item["category"] = "食品・お菓子"
    data["items"] = guide_items + real_products
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    source = source[:match.start(1)] + encoded + source[match.end(1):]
    path.write_text(source, encoding="utf-8")


def update_sitemap():
    path = ROOT / "site-sitemap.xml"
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    tree = ET.parse(path)
    root = tree.getroot()
    urls = {item.findtext(f"{{{ns}}}loc"): item for item in root}
    for g in GUIDES:
        url = BASE + "/products/" + g["slug"] + ".html"
        node = urls.get(url)
        if node is None:
            node = ET.SubElement(root, f"{{{ns}}}url")
            ET.SubElement(node, f"{{{ns}}}loc").text = url
        modified = node.find(f"{{{ns}}}lastmod")
        if modified is None:
            modified = ET.SubElement(node, f"{{{ns}}}lastmod")
        modified.text = PUBLISHED
    tree.write(path, encoding="utf-8", xml_declaration=True)


def main():
    for g in GUIDES:
        (ROOT / "products" / (g["slug"] + ".html")).write_text(page(g), encoding="utf-8")
    update_index()
    update_sitemap()
    print(f"Rendered {len(GUIDES)} maintained guides; editorial date {PUBLISHED}")


if __name__ == "__main__":
    main()
