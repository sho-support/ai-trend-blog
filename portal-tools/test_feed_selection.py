#!/usr/bin/env python3
"""Verify stable shelf choices without keeping old prices or expired referrals."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import refresh_rakuten as refresh


class Selection(unittest.TestCase):
    def setUp(self):
        self.objects=[{'itemCode':'shop:'+str(i),'itemName':'24インチ IPS モニター '+str(i),
                       'itemPrice':10000+i,'affiliateUrl':'https://hb.afl.rakuten.co.jp/new-'+str(i),
                       'mediumImageUrls':['https://example.test/current-'+str(i)+'.jpg']}
                      for i in range(8)]
        self.previous=[{'id':'rakuten-shop-6','kind':'monitor','source':'rakuten','price_yen':1,
                        'expires_at':'2000-01-01T00:00:00Z','url':'https://hb.afl.rakuten.co.jp/old'}]

    def test_previous_products_use_current_objects_and_stable_order(self):
        rows=refresh.prefer_previous(self.objects,self.previous,'monitor')
        self.assertIs(rows[0],self.objects[6])
        self.assertEqual(rows[0]['itemPrice'],10006)
        self.assertEqual([x['itemCode'] for x in rows[1:]],['shop:'+str(i) for i in [0,1,2,3,4,5,7]])

    def test_missing_product_is_not_reinserted(self):
        rows=refresh.prefer_previous(self.objects[:3],self.previous,'monitor')
        self.assertEqual(rows,self.objects[:3])

    def test_another_genre_and_a8_cannot_override_this_shelf(self):
        for change in [{'kind':'gaming-monitor'},{'source':'a8'}]:
            rows=refresh.prefer_previous(self.objects,[dict(self.previous[0],**change)],'monitor')
            self.assertEqual(rows,self.objects)

    def test_wrapped_and_invalid_api_entries(self):
        wrapped=[None,{'item':None},{'item':self.objects[6]},self.objects[0]]
        rows=refresh.prefer_previous(wrapped,self.previous,'monitor')
        self.assertEqual(rows[0],{'item':self.objects[6]})
        self.assertEqual(refresh.item_object({'item':None}),{})

    def run_refresh(self, objects):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'feed.json'
            path.write_text(json.dumps({'items':self.previous}))
            response=lambda *args,**kwargs:contextlib.nullcontext(io.StringIO(json.dumps({'items':objects})))
            with patch.object(refresh,'OUT',path),patch.object(refresh,'SEARCHES',[refresh.CATEGORIES[0]]),\
                 patch.object(refresh,'urlopen',response),patch.dict(refresh.os.environ,{'RAKUTEN_APP_ID':'test-app','RAKUTEN_ACCESS_KEY':'test-key','RAKUTEN_AFFILIATE_ID':'test-affiliate'}),\
                 contextlib.redirect_stdout(io.StringIO()):
                # Pick the actual monitor shelf, not a neighbouring product genre.
                with patch.object(refresh,'SEARCHES',[next(x for x in refresh.CATEGORIES if x['key']=='monitor')]):
                    result=refresh.main()
            return result,json.loads(path.read_text())

    def test_refresh_revalidates_price_url_and_expiry(self):
        result,feed=self.run_refresh(self.objects)
        self.assertEqual(result,0)
        current=feed['items'][0]
        self.assertEqual(current['id'],'rakuten-shop-6')
        self.assertEqual(current['price_yen'],10006)
        self.assertEqual(current['url'],self.objects[6]['affiliateUrl'])
        self.assertEqual(current['image'],self.objects[6]['mediumImageUrls'][0])
        self.assertNotEqual(current['expires_at'],self.previous[0]['expires_at'])
        self.assertEqual(len(feed['items']),3)

    def test_preferred_item_still_must_pass_price_and_genre_checks(self):
        for patch in [{'itemPrice':0},{'itemName':'モニターアーム'}]:
            objects=[dict(x,**patch) if i==6 else x for i,x in enumerate(self.objects)]
            result,feed=self.run_refresh(objects)
            self.assertEqual(result,0)
            self.assertNotIn('rakuten-shop-6',{x['id'] for x in feed['items']})


if __name__=='__main__':unittest.main()
