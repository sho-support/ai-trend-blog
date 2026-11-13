"""Keep preview announcements, marketplace offers and dates separate."""
import json
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from black_friday import ROOT, HUB, checked_data, build_pages, entry_link
from build_storefront import document, category_cards, seed, tile_seed


class BlackFriday(unittest.TestCase):
    def render(self, data=None, now='2026-11-14T12:00:00+09:00'):
        self.scratch=tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        root=Path(self.scratch.name)
        (root/'deals').mkdir()
        (root/'portal-tools').mkdir()
        (root/'portal-assets').mkdir()
        for name in ('rakuten-feed.json','product-copy.json'):
            (root/'portal-assets'/name).write_text((ROOT/'portal-assets'/name).read_text())
        (root/'portal-tools/black-friday-2026.json').write_text(json.dumps(data or checked_data(),ensure_ascii=False))
        inventory=build_pages(document,category_cards,seed,tile_seed,root,datetime.fromisoformat(now))
        return root,inventory

    def test_amazon_news_does_not_copy_a_brands_amazon_store_schedule(self):
        root,rows=self.render()
        news=(root/'deals/amazon-black-friday-2026.html').read_text()
        self.assertIn('11月19日',news)
        self.assertNotIn('11月20日',news)
        self.assertNotIn('11月27日',news)
        self.assertNotIn('11月24日',news)
        self.assertNotIn('tag=',news)
        self.assertEqual(len(rows),4)

    def test_rakuten_entry_and_eligible_purchase_windows_are_distinct(self):
        data=checked_data()
        row=next(row for row in data['campaigns'] if row['id']=='rakuten')
        self.assertEqual(row['entry_starts_at'],'2026-11-12T10:00:00+09:00')
        self.assertEqual(row['starts_at'],'2026-11-19T20:00:00+09:00')
        self.assertEqual(row['ends_at'],'2026-11-25T02:00:00+09:00')
        root,_=self.render(data)
        article=(root/'deals/rakuten-black-friday-2026.html').read_text()
        self.assertIn('事前エントリーは、すでに受付中',article)
        self.assertIn('11月19日20時から25日1時59分',article)
        self.assertIn('7,000ポイント',article)
        self.assertNotIn('楽天は日程確認中',(root/HUB).read_text())

    def test_campaigns_are_first_party_news_without_unapproved_affiliate_material(self):
        data=checked_data()
        root,_=self.render(data)
        hub=(root/HUB).read_text()
        self.assertIn('11/29 25:59',hub)
        yahoo=next(row for row in data['campaigns'] if row['id']=='yahoo')
        self.assertEqual(datetime.fromisoformat(yahoo['ends_at']).isoformat(),'2026-11-30T02:00:00+09:00')
        self.assertNotIn('hb.afl.rakuten.co.jp',hub.split('window.CATALOG_INITIAL=')[0])
        self.assertNotIn('最大63%',hub)
        self.assertNotIn('2025年11月',hub)
        self.assertIn('現在の掲載商品です。ブラックフライデーの対象商品は未確認です。',hub)

    def test_wrong_sources_and_unreviewed_campaign_ads_are_rejected(self):
        for change in ({'source':'https://www.aboutamazon.jp.attacker.example/news'},
                       {'affiliate_url':'https://px.a8.net/unconfirmed'}):
            data=deepcopy(checked_data());data['campaigns'][0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):self.render(data)

    def test_expired_seasonal_hub_is_archived_and_its_promo_entry_disappears(self):
        root,rows=self.render(now='2026-12-12T00:00:00+09:00')
        hub=(root/HUB).read_text()
        self.assertIn('開催記録',hub)
        self.assertIn('noindex,follow',hub)
        self.assertNotIn('data-category=',hub)
        self.assertTrue(all(row['indexable'] is False for row in rows))
        self.assertEqual(entry_link(datetime.fromisoformat('2026-12-12T00:00:00+09:00')),'')
        self.assertIn('black-friday-2026.html',entry_link(datetime.fromisoformat('2026-12-11T23:59:59+09:00')))

    def test_archived_seasonal_pages_are_excluded_from_commercial_sitemaps(self):
        import build_commercial_site as commercial
        from unittest.mock import patch
        root,_=self.render(now='2026-12-12T00:00:00+09:00')
        (root/'products').mkdir()
        (root/'deals/index.html').write_text('<h1>お得情報</h1>')
        with patch.object(commercial,'DIST',root):commercial.make_sitemap()
        sitemap=(root/'sitemap.xml').read_text()
        self.assertNotIn('black-friday-2026.html',sitemap)


if __name__=='__main__':unittest.main()
