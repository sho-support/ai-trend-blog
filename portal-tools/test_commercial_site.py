"""Verify migration gates and the destination's canonical URL behavior."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_commercial_site as site


class CommercialSite(unittest.TestCase):
    def test_old_media_a8_material_blocks_a_new_production_host(self):
        import json
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'portal-assets').mkdir()
            item={'id':'a8-test','title':'商品','kind':'cookware','approved':True,'affiliate':True,'site_registered':True,'material_type':'free_link',
                  'site_url':site.SOURCE_BASE+'/products/','url':'https://px.a8.net/svt/ejp?test','expires_at':'2099-01-01T00:00:00+09:00'}
            (root/'portal-assets/a8-approved.json').write_text(json.dumps({'items':[item]}))
            with patch.object(site,'ROOT',root),patch.object(site,'BASE','https://store.example'),patch.object(site,'PREVIEW',False):
                with self.assertRaisesRegex(SystemExit,'old media'):site.check_media_scope()

    def test_new_origin_does_not_rewrite_a8_media_approval(self):
        old=site.SOURCE_BASE
        with patch.object(site,'BASE','https://store.example'),patch.object(site,'PAGES',True):
            moved=site.rebase('{"site_url":"'+old+'/products/","url":"'+old+'/products/item.html"}')
        self.assertIn('"site_url":"'+old+'/products/"',moved)
        self.assertIn('"url":"https://store.example/products/item"',moved)

    def test_preview_keeps_photos_but_removes_ad_navigation_and_analytics(self):
        body='''<html><head><script async src="https://www.googletagmanager.com/gtag/js?id=test"></script>
        <script>window.CATALOG_INITIAL={"url":"https://hb.afl.rakuten.co.jp/ad"}</script>
        <script type="application/ld+json">{"@type":"WebPage"}</script></head><body>
        <img src="https://image.example/product.jpg" alt="商品">
        <a href="https://hb.afl.rakuten.co.jp/ad" rel="sponsored">価格を見る</a>
        <a href="https://px.a8.net/ad">公式で見る</a>
        <a href="https://event.rakuten.co.jp/">公式の発表</a></body></html>'''
        output=site.preview_page(body)
        self.assertIn('product.jpg',output)
        self.assertNotIn('googletagmanager',output)
        self.assertNotIn('CATALOG_INITIAL',output)
        self.assertNotIn('href="https://hb.afl',output)
        self.assertNotIn('href="https://px.a8',output)
        self.assertIn('href="https://event.rakuten.co.jp/"',output)
        self.assertEqual(output.count('aria-disabled="true" tabindex="-1"'),2)

    def test_pages_sitemap_matches_extensionless_canonicals_and_skips_noindex(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'deals').mkdir();(root/'products').mkdir()
            (root/'deals/news.html').write_text('<h1>開催日</h1>')
            (root/'products/search.html').write_text('<meta name="robots" content="noindex,follow">')
            with patch.object(site,'DIST',root),patch.object(site,'BASE','https://store.example'),patch.object(site,'PAGES',True),patch.object(site,'PREVIEW',False):
                site.make_sitemap()
            output=(root/'sitemap.xml').read_text()
            self.assertIn('https://store.example/deals/news</loc>',output)
            self.assertNotIn('.html',output)
            self.assertNotIn('search',output)

    def test_preview_is_excluded_from_search_and_does_not_ship_affiliate_feeds(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'source';dist=Path(temp)/'dist'
            (root/'portal-assets').mkdir(parents=True);(root/'portal-tools').mkdir()
            dist.mkdir();(dist/'portal-assets').mkdir()
            for folder in site.PORTAL_FOLDERS:
                (root/folder).mkdir();(root/folder/'index.html').write_text('<html><head></head><body>商品</body></html>')
            for file in site.ASSET_FILES:(root/'portal-assets'/file).write_text('{}' if file.endswith('.json') else '')
            (root/'portal-tools/indexnow_config.json').write_text('{"key":"public-key"}')
            (root/'public-key.txt').write_text('public-key')
            with patch.object(site,'ROOT',root),patch.object(site,'DIST',dist),patch.object(site,'PREVIEW',True):
                site.copy_pages();site.make_sitemap()
            self.assertFalse((dist/'portal-assets/rakuten-feed.json').exists())
            self.assertFalse((dist/'portal-assets/a8-approved.json').exists())
            self.assertNotIn('<loc>',(dist/'sitemap.xml').read_text())
            self.assertIn('Disallow: /',(dist/'robots.txt').read_text())


if __name__=='__main__':unittest.main()
