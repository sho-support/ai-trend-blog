"""Only fresh, affiliate-approved API observations can produce point cards."""
import unittest
from datetime import datetime,timezone
from deal_news import point_offers,render_points

NOW=datetime(2026,11,14,6,tzinfo=timezone.utc)
class PointOffers(unittest.TestCase):
    def setUp(self):
        self.item=dict(id='example',source='rakuten',title='商品',price_yen=1000,
          approved=True,affiliate=True,url='https://hb.afl.rakuten.co.jp/test',
          image='https://thumbnail.image.rakuten.co.jp/test.jpg',verified='2026-11-14',
          expires_at='2026-11-15T01:00:00+09:00',point_rate=10)
    def rows(self,**patch):return point_offers({'items':[dict(self.item,**patch)]},{},NOW)
    def test_no_prices_are_recast_as_cash_discounts(self):
        html=render_points(self.rows())
        self.assertIn('10倍',html)
        self.assertIn('現金値引きではありません',html)
        self.assertNotIn('900円',html)
        self.assertNotIn('OFF',html)
    def test_stale_or_unapproved_observations_are_hidden(self):
        for patch in [dict(approved=False),dict(affiliate=False),dict(expires_at=NOW.isoformat()),dict(point_rate=1),dict(point_end='2026-11-13T00:00:00+09:00')]:
            self.assertEqual(self.rows(**patch),[])
    def test_legacy_official_api_description_is_supported(self):
        rows=self.rows(point_rate=None,description='API掲載ポイント倍率: 5倍。')
        self.assertEqual(rows[0]['point_rate'],5)
    def test_seller_title_is_not_evidence_of_point_rate(self):
        self.assertEqual(self.rows(point_rate=None,title='ポイント20倍'),[])
if __name__=='__main__':unittest.main()
