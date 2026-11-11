"""Reviewed seasonal news. No guessed dates, discounts or affiliate credentials."""
import html
import json
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from catalog_taxonomy import BY_KIND
from storefront_seo import inventory_entry, live

ROOT = Path(__file__).resolve().parents[1]
HUB = 'deals/black-friday-2026.html'
SOURCE_HOSTS = {
    'amazon': 'www.aboutamazon.jp',
    'rakuten': 'event.rakuten.co.jp',
    'yahoo': 'www.lycorp.co.jp',
    'ecoflow': 'jp.ecoflow.com',
}
E = lambda value: html.escape(str(value), quote=True)


def checked_data(root=ROOT):
    data = json.loads((root/'portal-tools/black-friday-2026.json').read_text())
    date.fromisoformat(data['checked_on'])
    if data['edition'] != 2026:
        raise ValueError('The reviewed edition is 2026')
    archive = datetime.fromisoformat(data['archive_after'])
    if archive.tzinfo is None:
        raise ValueError('The archive boundary must include its timezone')
    seen = set()
    for row in data['campaigns']:
        if row['id'] in seen or row['id'] not in SOURCE_HOSTS:
            raise ValueError('Invalid or duplicate campaign')
        seen.add(row['id'])
        source = urlsplit(row['source'])
        if source.scheme != 'https' or source.netloc != SOURCE_HOSTS[row['id']]:
            raise ValueError('Campaign news must cite its own first-party source')
        # A marketplace/API link is not approval for a direct-shop/SNS campaign.
        if row.get('affiliate_url'):
            raise ValueError('Campaign affiliate material has not been approved')
        for key in ('starts_at', 'ends_at'):
            if row.get(key) and datetime.fromisoformat(row[key]).tzinfo is None:
                raise ValueError('Campaign dates require a timezone')
        if row.get('starts_at') and row.get('ends_at') and datetime.fromisoformat(row['starts_at']) >= datetime.fromisoformat(row['ends_at']):
            raise ValueError('Invalid campaign period')
        if row.get('landing_url'):
            landing = urlsplit(row['landing_url'])
            if landing.scheme != 'https' or landing.netloc != 'shopping.yahoo.co.jp' or row['id'] != 'yahoo':
                raise ValueError('Unreviewed campaign destination')
        article = row.get('article')
        if article and (Path(article['file']).name != article['file'] or not article['file'].endswith('.html')):
            raise ValueError('Invalid article path')
    for kind in data['shelves']:
        if kind not in BY_KIND:
            raise ValueError('Unknown product shelf')
    return data


def campaign_card(row):
    link = row.get('landing_url') or row['source']
    more = ('<a class="text-link" href="'+E(row['article']['file'])+'">短い記事を読む →</a>'
            if row.get('article') else '')
    return ('<article class="offer-card"><span class="store-name">'+E(row['name'])+'</span>'
            '<h2>'+E(row['headline'])+'</h2><p class="bf-period">'+E(row['period'])+'</p>'
            '<p class="bf-summary">'+E(row['summary'])+'</p><div class="bf-links">'
            '<a class="text-link" href="'+E(link)+'" target="_blank" rel="noopener noreferrer">公式案内へ ↗</a>'
            +more+'</div></article>')


def build_pages(document, category_cards, seed, tile_seed, root=ROOT, now=None):
    data = checked_data(root)
    now = now or datetime.now(timezone.utc)
    archived = now >= datetime.fromisoformat(data['archive_after'])
    stamp = date.fromisoformat(data['checked_on'])
    checked = f'{stamp.month}月{stamp.day}日・公式発表を確認'
    inventory = []

    def save(path, title, body, description, **kwargs):
        page = document(title+'｜トクサーチ', path, body, brand='deals', description=description,
                        noindex=archived, **kwargs)
        page = page.replace('</head>', '<link rel="stylesheet" href="../portal-assets/black-friday.css"></head>')
        (root/path).write_text(page, encoding='utf-8')
        inventory.append(inventory_entry(path, page, not archived))

    heading = '2026年ブラックフライデーの開催記録' if archived else '今年のブラックフライデー、いつから？'
    intro = ('掲載した日程の特集は終了しました。<a href="./">いまのお得情報へ →</a>' if archived else
             'Amazon・楽天・Yahoo!ショッピング・EcoFlow。公式で確認できた日程をまとめました。')
    body = ('<div class="page-heading"><h1>'+heading+'</h1></div><p class="bf-lead">'+intro+'</p>'
            '<p class="bf-checked">'+E(checked)+'</p><div class="offer-grid bf-calendar">'
            +''.join(campaign_card(row) for row in data['campaigns'])+'</div>')
    scripts = ()
    initial = None
    config = None
    if not archived:
        feed = json.loads((root/'portal-assets/rakuten-feed.json').read_text())
        copies = json.loads((root/'portal-assets/product-copy.json').read_text())
        items = [x for x in feed['items'] if x.get('source') == 'rakuten' and live(x, now)]
        shelves = [BY_KIND[kind] for kind in data['shelves']]
        photos = tile_seed(shelves, items)
        body += ('<section class="bf-shelves"><div class="page-heading"><h2>楽天の商品をジャンルから見る</h2>'
                 '<span class="ad-label">PR</span></div><p class="bf-summary">現在の掲載商品です。ブラックフライデーの対象商品は未確認です。</p>'
                 +category_cards(shelves, prefix='../products/', items=items, copies=copies)+'</section>')
        scripts = ('catalog.js',)
        initial = seed(photos, copies)
        config = {'mode':'directory'}
    body += '<p class="bf-back"><a href="./">お得情報の一覧へ →</a></p>'
    save(HUB, 'ブラックフライデー2026｜発表された開催日をチェック', body,
         '2026年ブラックフライデーの公式発表を短く整理。Amazonは11月19日に詳細発表予定、Yahoo!ショッピングは11月22日から。楽天は日程確認中。',
         scripts=scripts, initial=initial, config=config)

    for row in data['campaigns']:
        if not row.get('article'):
            continue
        article = row['article']
        paragraphs = ''.join('<p>'+E(text)+'</p>' for text in article['paragraphs'])
        body = ('<article class="bf-story"><p class="breadcrumbs"><a href="black-friday-2026.html">ブラックフライデー2026</a></p>'
                '<h1>'+E(article['title'])+'</h1><p class="bf-checked">'+E(checked)+'</p>'
                +('<p class="bf-archive">この開催日程の特集は終了しました。</p>' if archived else '')
                +'<div class="bf-story-copy">'+paragraphs+'</div><a class="buy-button" href="'+E(row['source'])
                +'" target="_blank" rel="noopener noreferrer">'+E(article['button'])+' ↗</a>'
                '<p class="bf-source">出典：<a href="'+E(row['source'])+'" target="_blank" rel="noopener noreferrer">'
                +E(row['source_label'])+'</a></p><p class="bf-back"><a href="black-friday-2026.html">ほかの開催日も見る →</a></p></article>')
        save('deals/'+article['file'], article['title'], body, article['description'])
    return inventory


def entry_link(now=None):
    now = now or datetime.now(timezone.utc)
    data = checked_data()
    if now >= datetime.fromisoformat(data['archive_after']):
        return ''
    return '<a class="bf-entry" href="black-friday-2026.html">ブラックフライデー2026の開催情報 <span aria-hidden="true">→</span></a>'
