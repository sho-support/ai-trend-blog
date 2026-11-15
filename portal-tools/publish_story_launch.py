"""One reviewed photo post to the existing Monoyori X account, no write retry."""
import json
import os
import time
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import urlopen
from publish_product_launch import graphql_client,target_organization,find_post,FIELDS,CHANNEL_ID

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'growth/story-launch-receipt.json'

def save(value):
    OUT.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def main():
    request=json.loads((ROOT/'growth/story-launch.json').read_text())
    expected='https://sho-monoyori-review.zodiac-suu.workers.dev/products/stories/adjustable-dumbbells-how-to-choose'
    if request['article_url']!=expected or request['channel_id']!=CHANNEL_ID or '[PR]' not in request['text']:
        raise SystemExit('Unexpected destination or missing disclosure')
    if request['image_source']!='rakuten_affiliate_link_builder' or request['image_authorized'] is not True:
        raise SystemExit('The exact photograph must be verified in the official link builder')
    if datetime.fromisoformat(request['expires_at'])<=datetime.now(timezone.utc):
        raise SystemExit('Reviewed notice expired')
    with urlopen(expected,timeout=30) as r:
        body=r.read().decode()
        if r.status!=200 or 'review-mode.js' in body or 'data-buy=' not in body or '4商品の口コミ' not in body:
            raise SystemExit('The actual article and purchase route must be live first')
    # History is checked before the only mutation. A persisted ambiguous claim
    # must be reconciled, never automatically repeated.
    call=graphql_client(os.environ['BUFFER_API_KEY'])
    org=target_organization(call)
    prior=find_post(call,org,{'url':request['article_url'],'created_at':request['created_at']})
    if prior:
        save({'campaign_id':request['campaign_id'],'outcome':'existing','post':prior});print(json.dumps(prior));return
    if OUT.exists():raise SystemExit('Earlier attempt recorded; reconcile before retrying')
    save({'campaign_id':request['campaign_id'],'outcome':'attempt_started'})
    payload={'input':{'text':request['text'],'channelId':CHANNEL_ID,'schedulingType':'automatic','mode':'shareNow','aiAssisted':True,'assets':[{'image':{'url':request['image_url'],'metadata':{'altText':'ONE STEPの可変式ダンベル。楽天アフィリエイト公式リンク作成画面の掲載写真。'}}}],'needsApproval':False}}
    result=call('mutation($input:CreatePostInput!) { createPost(input:$input) { ... on PostActionSuccess { post { '+FIELDS+' } } ... on MutationError { message } } }',payload)
    post=result.get('createPost',{}).get('post')
    if not post or post.get('channelId')!=CHANNEL_ID:raise SystemExit('Post creation not confirmed; do not retry automatically')
    save({'campaign_id':request['campaign_id'],'outcome':'accepted','post':post})
    for _ in range(4):
        if post.get('status')=='sent' and post.get('externalLink') and post.get('assets'):break
        time.sleep(8)
        post=find_post(call,org,{'url':request['article_url'],'created_at':request['created_at']}) or post
    receipt={'campaign_id':request['campaign_id'],'outcome':'published' if post.get('status')=='sent' and post.get('externalLink') and post.get('assets') else 'accepted_only','post':post}
    save(receipt);print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
