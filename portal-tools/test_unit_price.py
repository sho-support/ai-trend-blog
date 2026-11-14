import unittest
from storefront_seo import unit_price

class UnitPriceTests(unittest.TestCase):
    def test_half_yen_cent_rounds_same_as_browser(self):
        self.assertIn('53.13',unit_price({'id':'rakuten-lifedrinkcompany-10000022','price_yen':2550}))
    def test_price_updates_change_unit_price(self):
        self.assertIn('50.00',unit_price({'id':'rakuten-lifedrinkcompany-10000022','price_yen':2400}))
    def test_unknown_pack_is_not_guessed(self):
        self.assertEqual('',unit_price({'id':'unknown','price_yen':2400}))
if __name__=='__main__':unittest.main()
