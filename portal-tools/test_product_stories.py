import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class StoryTests(unittest.TestCase):
    def test_home_has_categories_before_articles_and_no_fixed_product_hero(self):
        body=(ROOT/'products/index.html').read_text()
        self.assertNotIn('hero-product',body)
        self.assertNotIn('editorial-picks-grid',body)
        self.assertLess(body.index('id="departments"'),body.index('SHOPPING JOURNAL'))
    def test_articles_are_linked_and_explicit_about_experience(self):
        from product_stories import STORIES
        home=(ROOT/'products/index.html').read_text()
        for story in STORIES:
            self.assertIn('stories/'+story['slug']+'.html',home)
            body=(ROOT/'products/stories'/(story['slug']+'.html')).read_text()
            self.assertIn('BlogPosting',body)
            self.assertIn('実食・実機使用レビューではありません',body)
            self.assertIn('確認した情報源',body)
            self.assertIn('掲載商品の価格・販売条件',body)
if __name__=='__main__':unittest.main()
