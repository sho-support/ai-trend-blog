#!/usr/bin/env python3
"""Exercise notice validation, recipient matching and ambiguous-write handling."""
import json
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from publish_product_launch import CHANNEL_ID, HANDLE, launch, validate

ROOT = Path(__file__).resolve().parents[1]


class Buffer:
    def __init__(self, existing=False, status='sent', fail_write=False, locked=False):
        self.existing=existing; self.status=status; self.fail_write=fail_write; self.locked=locked; self.writes=0

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
            assert variables['input']['assets']==[]
            return {'createPost':{'post':self.post()}}
        raise AssertionError('Unexpected API request')

    def post(self):
        return {'id':'test-post', 'text':self.request['text'], 'status':self.status,
                'channelId':CHANNEL_ID, 'externalLink':'https://x.com/AITrendBlogJP/status/123' if self.status=='sent' else None,
                'sentAt':'2026-11-02T00:00:00Z' if self.status=='sent' else None}


class ProductLaunch(unittest.TestCase):
    def setUp(self):
        self.request=json.loads((ROOT/'growth/x-launch.json').read_text())
        self.item=next(x for x in json.loads((ROOT/'portal-assets/a8-approved.json').read_text())['items']
                       if x['id']==self.request['product_id'])
        # Isolated test data, never written to the actual catalogue or publisher request.
        self.item['expires_at']='2099-01-02T00:00:00Z'
        self.request['expires_at']='2099-01-01T00:00:00Z'
        self.now=datetime(2026,11,2,tzinfo=timezone.utc)

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
        self.assertTrue(result['external_url'].startswith('https://x.com/AITrendBlogJP/status/'))

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


if __name__=='__main__':unittest.main()
