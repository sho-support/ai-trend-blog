import unittest
from prepare_live import merge_feed

class FeedPromotion(unittest.TestCase):
    def test_new_price_keeps_a_dated_atomic_rating_snapshot(self):
        old={'items':[{'id':'one','price_yen':100,'review_average':4.5,'review_count':20,'verified':'2026-11-14','expires_at':'2026-11-15T00:00:00+09:00'}]}
        new={'items':[{'id':'one','price_yen':150,'review_average':None,'review_count':25,'verified':'2026-11-16','expires_at':'2026-11-17T00:00:00+09:00'}]}
        row=merge_feed(new,old)['items'][0]
        self.assertEqual((row['price_yen'],row['review_average'],row['review_count'],row['rating_verified']),(150,4.5,20,'2026-11-14'))
        self.assertEqual(row['expires_at'],'2026-11-17T00:00:00+09:00')
    def test_expired_manual_offer_is_not_revived(self):
        old={'items':[{'id':'gone','verification_method':'merchant_page','expires_at':'2000-01-01T00:00:00+09:00'}]}
        self.assertEqual(merge_feed({'items':[]},old)['items'],[])
    def test_fresh_api_rating_wins(self):
        row=merge_feed({'items':[{'id':'one','review_average':4.1,'review_count':30}]},{'items':[{'id':'one','review_average':4.5,'review_count':20}]})['items'][0]
        self.assertEqual((row['review_average'],row['review_count']),(4.1,30))

if __name__=='__main__':unittest.main()
