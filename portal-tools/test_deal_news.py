#!/usr/bin/env python3
"""Price-news eligibility, SSR and browser selector parity; never calls an API."""
import json
import subprocess
import unittest
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from pathlib import Path

from deal_news import selected_deals,render_deals
from track_prices import observed_drop

ROOT=Path(__file__).resolve().parents[1]
NOW=datetime(2026,11,4,4,tzinfo=timezone.utc)


class Deals(unittest.TestCase):
    def setUp(self):
        self.item={'id':'test-speaker','source':'rakuten','category':'オーディオ','title':'SoundCore スピーカー',
                   'price_yen':4193,'url':'https://hb.afl.rakuten.co.jp/test','approved':True,'affiliate':True,
                   'image':'https://thumbnail.image.rakuten.co.jp/test.jpg?_ex=128x128','verified':'2026-11-04',
                   'expires_at':'2026-11-05T00:00:00Z',
                   'verified_deal':{'previous_observed_low_yen':5990,'current_yen':4193}}
        self.history={'items':{'test-speaker':[{'date':d,'price':5990} for d in ('2026-10-31','2026-11-01','2026-11-03')]+[{'date':'2026-11-04','price':4193}]}}
        self.copies={'test-speaker':{'name':'SoundCore 2','description':'短い紹介。'}}

    def both(self,item=None,history=None,now=NOW):
        feed={'items':[item or self.item]};history=history or self.history
        result=selected_deals(feed,history,self.copies,now)
        script="const {selectedDeals}=require('./portal-assets/deal-news.js');let b='';process.stdin.on('data',x=>b+=x);process.stdin.on('end',()=>{const x=JSON.parse(b);process.stdout.write(JSON.stringify(selectedDeals(x.feed,x.history,x.copies,x.now)))});"
        browser=json.loads(subprocess.check_output(['node','-e',script],cwd=ROOT,input=json.dumps({'feed':feed,'history':history,'copies':self.copies,'now':now.timestamp()*1000}).encode()))
        self.assertEqual(result,browser)
        return result

    def test_verified_drop_renders_photo_price_and_direct_advertisement(self):
        rows=self.both();self.assertEqual(len(rows),1)
        page=render_deals(rows)
        self.assertIn('4,193円',page);self.assertIn('5,990円',page)
        self.assertIn('600x600',page);self.assertIn('rel="noopener noreferrer sponsored"',page)
        self.assertNotIn('/products/items/',page)
        self.assertNotIn('%OFF',page)

    def test_stale_or_unapproved_prices_cannot_stay_visible(self):
        for patch in ({'expires_at':NOW.isoformat()},{'approved':False},{'affiliate':False},
                      {'price_yen':0},{'url':'https://example.test'},{'verified':'not-a-date'}):
            with self.subTest(patch=patch):self.assertEqual(self.both(dict(self.item,**patch)),[])

    def test_no_invented_reference_price_or_unverified_discount(self):
        for deal in ({},{'previous_observed_low_yen':10000,'current_yen':4193},
                     {'previous_observed_low_yen':5990,'current_yen':4000}):
            with self.subTest(deal=deal):self.assertEqual(self.both(dict(self.item,verified_deal=deal)),[])
        old=deepcopy(self.history);old['items']['test-speaker']=old['items']['test-speaker'][:2]
        self.assertEqual(self.both(history=old),[])
        self.assertEqual(self.both(dict(self.item,price_yen=5990)),[])

    def test_same_price_keeps_original_comparison_for_three_jst_dates(self):
        history=deepcopy(self.history)
        records=history['items']['test-speaker']
        for offset in (1,2,3):
            now=NOW+timedelta(days=offset)
            day=now.date()
            records.append({'date':day.isoformat(),'price':4193})
            deal=observed_drop(records,day,4193)
            item=dict(self.item,verified=day.isoformat(),verified_deal=deal,
                      expires_at=(now+timedelta(hours=23)).isoformat())
            rows=self.both(item,history,now)
            if offset==3:
                self.assertIsNone(deal)
                self.assertEqual(rows,[])
            else:
                self.assertEqual(len(rows),1)
                self.assertEqual(deal['first_observed_date'],'2026-11-04')
                self.assertEqual(rows[0]['previous_price'],5990)
                self.assertEqual(rows[0]['previous_date'],'2026-11-03')
                self.assertEqual(rows[0]['news_expires_at'],'2026-11-07T00:00:00+09:00')

    def test_expiry_and_new_history_hide_an_old_price(self):
        old=deepcopy(self.history)
        records=old['items']['test-speaker']
        for day in ('2026-11-05','2026-11-06'):
            records.append({'date':day,'price':4193})
        deal=observed_drop(records,datetime(2026,11,6).date(),4193)
        item=dict(self.item,verified='2026-11-06',verified_deal=deal,
                  expires_at='2026-11-07T12:00:00+09:00')
        before=datetime.fromisoformat('2026-11-06T23:59:59+09:00')
        self.assertEqual(len(self.both(item,old,before)),1)
        self.assertEqual(self.both(item,old,before+timedelta(seconds=1)),[])

        records[-1]['price']=5990
        self.assertEqual(self.both(item,old,before),[])
        records[-1]['price']=4193
        records.append({'date':'2026-11-07','price':5990})
        self.assertEqual(self.both(item,old,before),[])

    def test_missing_date_or_price_increase_cannot_restart_drop(self):
        for extra in ([],[{'date':'2026-11-05','price':4293}]):
            records=self.history['items']['test-speaker']+extra+[{'date':'2026-11-06','price':4193}]
            self.assertIsNone(observed_drop(records,datetime(2026,11,6).date(),4193))
        records=self.history['items']['test-speaker']+[{'date':'2026-11-05','price':4500}]
        self.assertIsNone(observed_drop(records,datetime(2026,11,5).date(),4500))


if __name__=='__main__':unittest.main()
