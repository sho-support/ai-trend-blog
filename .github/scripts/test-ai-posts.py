#!/usr/bin/env python3
"""Offline regressions for fresh, concise, correctly routed AI posts."""
import json
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import publish_to_buffer as news


class Posts(unittest.TestCase):
    def test_copy_needs_no_gemini_key_or_call(self):
        data=json.loads((ROOT/'editorial/beginner-guides.json').read_text())
        for guide in data['guides']:
            text=news.create_post_copy({'filename':guide['slug']+'.html','social_copy':guide['social_copy']})
            self.assertLessEqual(news.x_weighted_length(text),270)
            self.assertIn(guide['social_copy'],text)
            self.assertEqual(text.count('https://'),1)
            self.assertNotIn('稼げる',text)

    def test_old_or_future_articles_are_not_recycled(self):
        now=datetime(2026,11,4,tzinfo=timezone.utc)
        self.assertTrue(news.is_fresh({'created_at':(now-timedelta(days=1)).isoformat()},now))
        for stamp in ((now-timedelta(days=4)).isoformat(),(now+timedelta(minutes=1)).isoformat(),'broken','2026-11-04'):
            with self.subTest(stamp=stamp):self.assertFalse(news.is_fresh({'created_at':stamp},now))

    def test_revenue_guarantees_and_path_changes_are_rejected(self):
        for row in ({'filename':'../products/test.html','title':'テスト'},
                    {'filename':'test.html','social_copy':'誰でも稼げる'}):
            with self.assertRaises(ValueError):news.create_post_copy(row)

    def test_single_available_channel_is_not_an_account_fallback(self):
        with patch.object(news,'buffer_graphql',side_effect=[
                {'account':{'organizations':[{'id':'0'*24}]}},
                {'channels':[{'id':'other','service':'twitter','externalLink':'https://x.com/other'}]}]):
            with self.assertRaises(RuntimeError):news.get_x_channel_id()


if __name__=='__main__':unittest.main()
