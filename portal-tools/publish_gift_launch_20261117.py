"""One reviewed photo post to the existing Monoyori X account, no write retry."""
import json
import os
import time
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import urlopen
from publish_product_launch import graphql_client,target_organization,find_post,FIELDS,CHANNEL_ID

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'growth/gift-launch-20261117-receipt.json'

def save(value):
    OUT.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def main():
    request=json.loads((ROOT/'growth/gift-launch-20261117.json').read_text())
    expected='https://sho-monoyori-review.zodiac-suu.workers.dev/products/stories/yokumoku-delices-gift'
    if request['article_url']!=expected or request['channel_id']!=CHANNEL_ID or '[PR]' not in request['text']:
        raise SystemExit('Unexpected destination or missing disclosure')
    if request['image_source']!='monoyori_original_editorial' or request['image_url']!='https://raw.githubusercontent.com/sho-support/ai-trend-blog/main/growth/social-assets/gift-check-pinterest.png' or request['image_authorized'] is not True:
        raise SystemExit('Use only the original editorial comparison graphic')
    if datetime.fromisoformat(request['expires_at'])<=datetime.now(timezone.utc):
        raise SystemExit('Reviewed notice expired')
    proof=json.loads(Path(os.environ['STORY_PUBLIC_PROOF']).read_text())
    age=time.time()-proof.get('checked_at',0)
    body=proof.get('html','')
    if proof.get('url')!=expected or proof.get('status')!=200 or not 0<=age<300 or 'review-mode.js' in body or 'data-buy=' not in body or '40個は何人分？' not in body:
        raise SystemExit('The actual article and purchase route must be freshly verified by the public browser')
    # History is checked before the only mutation. A persisted ambiguous claim
    # must be reconciled, never automatically repeated.
    call=graphql_client(os.environ['BUFFER_API_KEY'])
    org=target_organization(call)
    recent=call('query($input:PostsInput!) { posts(first:50,input:$input) { edges { node { '+FIELDS+' } } } }',{'input':{'organizationId':org,'filter':{'channelIds':[CHANNEL_ID],'startDate':request['created_at']},'sort':[{'field':'createdAt','direction':'desc'}]}})
    now=datetime.now(timezone.utc)
    for edge in recent.get('posts',{}).get('edges',[]):
        p=edge['node']
        if p.get('status')=='sent' and p.get('sentAt') and (now-datetime.fromisoformat(p['sentAt'].replace('Z','+00:00'))).total_seconds()<86400:
            raise SystemExit('A channel post remains inside the 24-hour cooldown; no mutation')
    prior=find_post(call,org,{'url':request['article_url'],'created_at':request['created_at']})
    if prior:
        save({'campaign_id':request['campaign_id'],'outcome':'existing','post':prior});print(json.dumps(prior));return
    if OUT.exists():raise SystemExit('Earlier attempt recorded; reconcile before retrying')
    save({'campaign_id':request['campaign_id'],'outcome':'attempt_started'})
    payload={'input':{'text':request['text'],'channelId':CHANNEL_ID,'schedulingType':'automatic','mode':'shareNow','aiAssisted':True,'assets':[{'image':{'url':request['image_url'],'metadata':{'altText':'職場に配るお菓子の確認点。人数と個数、個包装と内訳、配送日の3項目。'}}}],'needsApproval':False}}
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
