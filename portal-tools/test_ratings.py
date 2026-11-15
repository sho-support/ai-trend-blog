"""Ratings carry a marketplace source and never invent missing review scores."""
import unittest
from storefront_seo import rating, card_notes
class Ratings(unittest.TestCase):
    def test_rakuten_rating_includes_count_and_observation_date(self):
        html=rating(dict(source='rakuten',review_average=4.53,review_count=2316,verified='2026-11-13',rating_verified='2026-11-14'))
        for text in ('4.53','2,316','楽天市場','2026-11-14','販売ページ全体'):self.assertIn(text,html)
    def test_missing_invalid_or_non_rakuten_scores_are_not_published(self):
        for patch in ({'review_average':None},{'review_average':0},{'review_average':6},{'review_count':0},{'source':'a8'}):
            with self.subTest(patch=patch):self.assertNotIn('★',rating(dict(dict(source='rakuten',review_average=4.5,review_count=25),**patch)))
    def test_count_remains_visible_without_a_score(self):
        html=rating(dict(source='rakuten',review_count=1234))
        self.assertIn('1,234',html)
        self.assertIn('平均点は未取得',html)
        self.assertNotIn('★',html)
    def test_unknown_is_not_zero(self):
        self.assertIn('未確認',rating(dict(source='rakuten')))
        self.assertNotIn('0件',rating(dict(source='rakuten')))
    def test_editorial_notes_are_escaped(self):
        self.assertIn('&lt;script&gt;',card_notes(dict(card_reason='<script>')))
if __name__=='__main__':unittest.main()
