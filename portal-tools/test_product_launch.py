#!/usr/bin/env python3
"""Exercise notice validation, recipient matching and ambiguous-write handling."""
import json
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import publish_product_launch as publisher
from publish_product_launch import launch as actual_launch, validate as actual_validate, save_receipt

HANDLE='MonoyoriTest'
CHANNEL_ID='test-product-channel'
SOCIAL_LINKS=[]

def validate(request,items,now=None):
    return actual_validate(request,items,now,social_links=SOCIAL_LINKS)

def launch(request,items,call,**kwargs):
    return actual_launch(request,items,call,social_links=SOCIAL_LINKS,**kwargs)

ROOT = Path(__file__).resolve().parents[1]


class Buffer:
    def __init__(self, existing=False, status='sent', fail_write=False, locked=False, missing_image=False):
        self.existing=existing; self.status=status; self.fail_write=fail_write; self.locked=locked; self.writes=0
        self.missing_image=missing_image

    def call(self, query, variables=None):
        if 'organizations' in query:
            return {'account':{'organizations':[{'id':'test-organization'}]}}
        if 'channels(' in query:
            return {'channels':[{'id':CHANNEL_ID,'service':'twitter','externalLink':'https://twitter.com/'+HANDLE,
                                 'isLocked':self.locked,'isDisconnected':False}]}
        if 'posts(' in query:
            nodes=[self.post()] if self.existing or self.writes else []
            return {'posts':{'edges':[{'node':x} for x in nodes], 'pageInfo':{'hasNextPage':False}}}
        if 'createPost' in query:
            self.writes+=1
            if self.fail_write:raise RuntimeError('Simulated unknown response')
            assert variables['input']['channelId']==CHANNEL_ID
            assert variables['input']['mode']=='shareNow'
            expected=([{'image':{'url':self.request['image_url'],
                       'metadata':{'altText':self.request['image_alt_text']}}}]
                      if self.request.get('image_url') else [])
            assert variables['input']['assets']==expected
            return {'createPost':{'post':self.post()}}
        raise AssertionError('Unexpected API request')

    def post(self):
        return {'id':'test-post', 'text':self.request['text'], 'status':self.status,
                'channelId':CHANNEL_ID, 'externalLink':'https://x.com/'+HANDLE+'/status/123' if self.status=='sent' else None,
                'sentAt':'2026-11-02T00:00:00Z' if self.status=='sent' else None,
                'assets':[{'id':'test-image','mimeType':'image/jpeg'}]
                         if self.request.get('image_url') and not self.missing_image else []}


class ProductLaunch(unittest.TestCase):
    def setUp(self):
        for name,value in [('HANDLE',HANDLE),('CHANNEL_ID',CHANNEL_ID)]:
            target=patch.object(publisher,name,value);target.start();self.addCleanup(target.stop)
        self.request=json.loads((ROOT/'growth/x-launch.json').read_text())
        for key in ('image_url','image_alt_text','require_image'):
            self.request.pop(key,None)
        self.request.update(handle=HANDLE,channel_id=CHANNEL_ID,url='https://px.a8.net/svt/test-x-specific-link')
        self.request['text']='【PR】テスト用の商品紹介。\n'+self.request['url']
        self.item=next(x for x in json.loads((ROOT/'portal-assets/a8-approved.json').read_text())['items']
                       if x['id']==self.request['product_id'])
        # Isolated test data, never written to the actual catalogue or publisher request.
        self.item['expires_at']='2099-01-02T00:00:00Z'
        self.request['expires_at']='2099-01-01T00:00:00Z'
        self.now=datetime(2026,11,2,tzinfo=timezone.utc)
        SOCIAL_LINKS[:]=[{'product_id':self.item['id'],'handle':HANDLE,'url':self.request['url'],
                         'provider':'a8','placement':'x','site_registered':True,'program_allowed':True,
                         'checked_at':'2026-11-01T00:00:00Z','expires_at':'2099-01-02T00:00:00Z'}]

    def api(self, **kwargs):
        api=Buffer(**kwargs);api.request=self.request;return api

    def test_approved_disclosed_notice(self):
        self.assertEqual(validate(self.request,[self.item],self.now)['id'],self.item['id'])

    def test_expired_or_unregistered_product_is_rejected(self):
        for patch in [{'expires_at':'2000-01-01T00:00:00Z'},{'approved':False},{'site_registered':False}]:
            with self.subTest(patch=patch),self.assertRaises(ValueError):
                validate(self.request,[dict(self.item,**patch)],self.now)

    def test_request_cannot_extend_advertisement(self):
        with self.assertRaises(ValueError):validate(dict(self.request,expires_at='2099-01-03T00:00:00Z'),[self.item],self.now)

    def test_no_different_channel_or_unreviewed_link(self):
        for patch in [{'channel_id':'other'},{'handle':'other'},{'url':'https://example.com/'},{'text':'広告表示なし'}]:
            with self.subTest(patch=patch),self.assertRaises(ValueError):
                validate(dict(self.request,**patch),[self.item],self.now)

    def test_existing_notice_does_not_send_again(self):
        api=self.api(existing=True)
        result=launch(self.request,[self.item],api.call,pause=lambda _:None)
        self.assertEqual(api.writes,0)
        self.assertEqual(result['outcome'],'existing_notice')

    def test_one_real_mutation_and_sent_receipt(self):
        api=self.api();receipts=[]
        result=launch(self.request,[self.item],api.call,write=receipts.append,pause=lambda _:None)
        self.assertEqual(api.writes,1)
        self.assertEqual(receipts[0]['outcome'],'attempt_started')
        self.assertEqual(result['outcome'],'published')
        self.assertTrue(result['external_url'].startswith('https://x.com/'+HANDLE+'/status/'))

    def with_image(self):
        self.request.update(image_url=self.item['image'], image_alt_text='商品の写真', require_image=True)

    def test_authorized_product_image_is_attached_once(self):
        self.with_image();api=self.api()
        result=launch(self.request,[self.item],api.call,pause=lambda _:None)
        self.assertEqual(api.writes,1)
        self.assertEqual(result['outcome'],'published')
        self.assertTrue(result['image_confirmed'])
        self.assertEqual(result['asset_count'],1)

    def test_unreviewed_or_unauthorized_image_is_rejected_before_sending(self):
        self.with_image()
        variants=[(dict(self.request,image_url='https://example.com/other.jpg'),self.item),
                  (self.request,dict(self.item,image_authorized=False)),
                  (dict(self.request,image_alt_text=''),self.item)]
        for request,item in variants:
            api=self.api()
            with self.subTest(request=request),self.assertRaises(ValueError):
                launch(request,[item],api.call,pause=lambda _:None)
            self.assertEqual(api.writes,0)

    def test_required_image_cannot_be_omitted(self):
        self.request['require_image']=True
        with self.assertRaises(ValueError):validate(self.request,[self.item],self.now)

    def test_missing_image_confirmation_is_recorded_without_a_second_write(self):
        self.with_image();api=self.api(missing_image=True);receipts=[]
        with self.assertRaises(RuntimeError):
            launch(self.request,[self.item],api.call,write=receipts.append,pause=lambda _:None)
        self.assertEqual(api.writes,1)
        self.assertEqual(receipts[-1]['outcome'],'image_unconfirmed')
        self.assertFalse(receipts[-1]['image_confirmed'])

    def test_ai_account_can_never_receive_product_notices(self):
        with patch.object(publisher,'HANDLE','AITrendBlogJP'), self.assertRaises(ValueError):
            validate(dict(self.request,handle='AITrendBlogJP'),[self.item],self.now)

    def test_website_link_and_missing_sns_registration_are_rejected(self):
        SOCIAL_LINKS[0]['site_registered']=False
        with self.assertRaises(ValueError):validate(self.request,[self.item],self.now)
        SOCIAL_LINKS[0]['site_registered']=True
        with self.assertRaises(ValueError):
            validate(dict(self.request,url='https://sho-support.github.io/ai-trend-blog/products/items/'+self.item['id']+'.html'),[self.item],self.now)

    def test_unknown_write_is_never_repeated(self):
        api=self.api(fail_write=True);receipts=[]
        with self.assertRaises(RuntimeError):launch(self.request,[self.item],api.call,write=receipts.append,pause=lambda _:None)
        self.assertEqual(api.writes,1)
        fresh=self.api()
        with self.assertRaises(RuntimeError):launch(self.request,[self.item],fresh.call,previous=receipts[0],pause=lambda _:None)
        self.assertEqual(fresh.writes,0)

    def test_locked_target_never_falls_back_to_another_account(self):
        api=self.api(locked=True)
        with self.assertRaises(ValueError):launch(self.request,[self.item],api.call,pause=lambda _:None)
        self.assertEqual(api.writes,0)

    def test_accepted_post_is_not_claimed_as_published(self):
        api=self.api(status='buffer')
        result=launch(self.request,[self.item],api.call,pause=lambda _:None)
        self.assertEqual(result['outcome'],'accepted_only')
        self.assertIsNone(result['external_url'])
        self.assertEqual(api.writes,1)

    def test_next_notice_keeps_the_previous_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'x-launch-receipt.json'
            first={'campaign_id':'monoyori_hario_test','post_id':'first','status':'sent'}
            second={'campaign_id':'monoyori_miffy_test','post_id':'second','status':'sent'}
            save_receipt(first,path)
            save_receipt(second,path)
            self.assertEqual(json.loads((path.parent/'x-launch-receipts/monoyori_hario_test.json').read_text()),first)
            self.assertEqual(json.loads(path.read_text()),second)

    def test_invalid_receipt_cannot_write_outside_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'x-launch-receipt.json'
            with self.assertRaises(ValueError):save_receipt({'campaign_id':'../bad'},path)
            self.assertFalse(path.exists())


if __name__=='__main__':unittest.main()
