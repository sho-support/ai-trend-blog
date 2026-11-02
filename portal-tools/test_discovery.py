#!/usr/bin/env python3
"""Check the HTML search crawlers receive, freshness, and notification scope."""
import json
import re
import unittest
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from storefront_seo import live, fingerprint
from catalog_taxonomy import BY_KIND
from notify_indexnow import changes, owned_url

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://sho-support.github.io/ai-trend-blog/'


class Document(HTMLParser):
    def __init__(self, body):
        super().__init__(); self.meta = {}; self.images = []; self.links = []; self.feed(body)

    def handle_starttag(self, tag, attrs):
        row = dict(attrs)
        if tag == 'meta': self.meta[row.get('name') or row.get('property')] = row.get('content')
        if tag == 'img': self.images.append(row)
        if tag == 'a': self.links.append(row)


class Discovery(unittest.TestCase):
    def test_current_product_content_does_not_require_javascript(self):
        items = json.loads((ROOT/'portal-assets/rakuten-feed.json').read_text())['items']
        items += json.loads((ROOT/'portal-assets/a8-approved.json').read_text())['items']
        copies = json.loads((ROOT/'portal-assets/product-copy.json').read_text())
        for item in filter(live, items):
            with self.subTest(id=item['id']):
                body = (ROOT/'products/items'/(item['id']+'.html')).read_text()
                page = Document(body)
                self.assertTrue(any(x.get('href') == item['url'] and 'sponsored' in x.get('rel','') for x in page.links))
                self.assertTrue(any(x.get('src') == item.get('image') for x in page.images))
                self.assertEqual(urlsplit(page.meta['og:image']).path, urlsplit(item['image']).path)
                self.assertEqual(page.meta['twitter:card'], 'summary_large_image')
                self.assertTrue(page.meta['description'])
                seed = json.loads(re.search(r'window.CATALOG_INITIAL=(\{.*?\});</script>',body).group(1))
                self.assertEqual(seed['items'][0]['expires_at'], item['expires_at'])
                self.assertTrue(any(x.get('alt') == copies[item['id']]['name'] for x in page.images))

    def test_search_and_retired_pages_are_not_in_sitemap(self):
        manifest = json.loads((ROOT/'portal-assets/discovery-manifest.json').read_text())
        urls = {x.text for x in ET.parse(ROOT/'site-sitemap.xml').getroot().iter() if x.tag.endswith('}loc')}
        self.assertFalse(BASE+'products/search.html' in urls,'Product search must stay out of the sitemap after every writer runs')
        self.assertEqual(Document((ROOT/'products/search.html').read_text()).meta['robots'],'noindex,follow')
        search=(ROOT/'products/search.html').read_text()
        lookup=json.loads(re.search(r'window.CATALOG_CATEGORIES=(\[.*?\]);',search).group(1))
        self.assertTrue(any(x['key']=='rice-cookers' and x['name']=='炊飯器' for x in lookup))
        for row in manifest['pages']:
            with self.subTest(url=row['url']):
                if row['indexable']: self.assertIn(row['url'],urls)
                else:
                    self.assertNotIn(row['url'],urls)
                    path = ROOT/row['url'].removeprefix(BASE)
                    page = Document(path.read_text())
                    self.assertEqual(page.meta['robots'],'noindex,follow')
                    self.assertFalse(any('sponsored' in x.get('rel','') for x in page.links))
                    self.assertFalse(page.images)

    def test_category_has_real_product_links_and_breadcrumbs(self):
        body = (ROOT/'products/okashi-matome.html').read_text()
        page = Document(body)
        self.assertTrue(any(x.get('href','').startswith('items/') for x in page.links))
        schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',body).group(1))
        types = {x['@type'] for x in schema['@graph']}
        self.assertIn('BreadcrumbList',types)
        self.assertIn('ItemList',types)
        self.assertNotIn('Review',types)

    def test_every_current_product_has_a_direct_shop_link_in_its_shelf(self):
        items = json.loads((ROOT/'portal-assets/rakuten-feed.json').read_text())['items']
        items += json.loads((ROOT/'portal-assets/a8-approved.json').read_text())['items']
        for item in filter(live, items):
            with self.subTest(id=item['id']):
                page = Document((ROOT/'products'/BY_KIND[item['kind']]['file']).read_text())
                links = [x for x in page.links if x.get('data-buy') == item['id']]
                self.assertEqual(len(links),1)
                self.assertEqual(links[0]['href'],item['url'])
                self.assertEqual(links[0]['target'],'_blank')
                self.assertIn('sponsored',links[0]['rel'])

    def test_notification_only_includes_our_site_and_changed_content(self):
        good = BASE+'products/'
        row = {'url':good,'fingerprint':fingerprint({'name':'商品'})}
        self.assertEqual(changes([row],{}),[row])
        self.assertEqual(changes([row],{good:row['fingerprint']}),[])
        for bad in ['https://px.a8.net/svt/ejp',BASE+'products/search.html?q=test',
                    'https://sho-support.github.io/other/',BASE+'../other/',BASE+'%2e%2e/other/']:
            self.assertFalse(owned_url(bad))
            with self.assertRaises(ValueError): changes([dict(row,url=bad)],{})

    def test_html_seed_uses_the_existing_expiration_without_renewing_it(self):
        item = deepcopy(json.loads((ROOT/'portal-assets/a8-approved.json').read_text())['items'][0])
        now = datetime(2026,11,1,tzinfo=timezone.utc)
        item['expires_at'] = (now-timedelta(seconds=1)).isoformat()
        self.assertFalse(live(item,now))
        item['expires_at'] = (now+timedelta(seconds=1)).isoformat()
        self.assertTrue(live(item,now))


if __name__ == '__main__': unittest.main()
