"""One-shot G335 product-photo campaign; fail closed and persist claim before send."""
import json,os,time,subprocess
from pathlib import Path
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from publish_product_launch import graphql_client,target_organization,FIELDS,CHANNEL_ID
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'growth/g335-photo-launch-20261128-receipt.json'
def save(v):OUT.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def history(call,org):
    after=None;posts=[]
    for _ in range(6):
        suffix=',after:'+json.dumps(after) if after else ''
        q='query($input:PostsInput!) { posts(first:50'+suffix+',input:$input) { edges { node { '+FIELDS+' } } pageInfo { hasNextPage endCursor } } }'
        r=call(q,{'input':{'organizationId':org,'filter':{'status':['sent'],'channelIds':[CHANNEL_ID],'dueAt':{'start':(datetime.now(timezone.utc)-timedelta(days=30)).isoformat()}},'sort':[{'field':'dueAt','direction':'desc'}]}})['posts']
        posts.extend(e['node'] for e in r['edges'])
        if not r['pageInfo']['hasNextPage']:return posts
        after=r['pageInfo'].get('endCursor')
        if not after:break
    raise SystemExit('Incomplete history; no send')
def main():
    r=json.loads((ROOT/'growth/g335-photo-launch-20261128.json').read_text())
    expected='https://sho-monoyori-review.zodiac-suu.workers.dev/products/items/rakuten-logicool-10000417'
    if r['article_url']!=expected or r['channel_id']!=CHANNEL_ID or not r['text'].startswith('[PR]'):raise SystemExit('Unexpected campaign')
    if r['image_source']!='rakuten_affiliate_item_link_builder' or r['image_authorized'] is not True or r['image_url']!='https://thumbnail.image.rakuten.co.jp/@0_mall/logicool/cabinet/white/g335bk.jpg?_ex=400x400':raise SystemExit('Unexpected image')
    if r['affiliate_url']!='https://a.r10.to/hPuUdX' or r['affiliate_url'] not in r['text'] or expected not in r['text']:raise SystemExit('Missing verified sales or article path')
    now=datetime.now(timezone.utc)
    if now<datetime.fromisoformat(r['not_before']):
        print('Prepared only; campaign not_before has not arrived');return
    if now>=datetime.fromisoformat(r['expires_at']):raise SystemExit('Expired campaign')
    proof=json.loads(Path(os.environ['STORY_PUBLIC_PROOF']).read_text())
    if proof['url']!=expected or proof['status']!=200 or not 0<=time.time()-proof['checked_at']<300 or not proof.get('passed'):raise SystemExit('Missing fresh public proof')
    call=graphql_client(os.environ['BUFFER_API_KEY']);org=target_organization(call)
    posts=history(call,org)
    known=[]
    for path in (ROOT/'growth').glob('*receipt*.json'):
        try:
            p=json.loads(path.read_text()).get('post') or {}
            if p.get('channelId')==CHANNEL_ID and p.get('status')=='sent' and p.get('sentAt'):known.append(p)
        except (ValueError,OSError):pass
    if known:
        latest=max(known,key=lambda p:p['sentAt'])
        if not any(p['id']==latest['id'] for p in posts):raise SystemExit('Latest receipt missing from API history; no send')
    for p in posts+known:
        if p.get('channelId')!=CHANNEL_ID or not p.get('sentAt'):raise SystemExit('Unexpected sent-history record')
        sent=datetime.fromisoformat(p['sentAt'].replace('Z','+00:00'))
        if (now-sent).total_seconds()<86400 or sent.astimezone(ZoneInfo('Asia/Tokyo')).date()==now.astimezone(ZoneInfo('Asia/Tokyo')).date():raise SystemExit('24h/daily limit; no send')
        if expected in p.get('text','') and (now-sent).days<14:raise SystemExit('URL already introduced inside 14 days')
    if OUT.exists():raise SystemExit('Earlier attempt exists; reconcile without resend')
    save({'campaign_id':r['campaign_id'],'outcome':'attempt_started','started_at':now.isoformat()})
    subprocess.run(['bash','.github/scripts/safe-commit-push.sh','Claim G335 real product-photo campaign before sending'],cwd=ROOT,check=True)
    post=call('mutation($input:CreatePostInput!) { createPost(input:$input) { ... on PostActionSuccess { post { '+FIELDS+' } } ... on MutationError { message } } }',{'input':{'text':r['text'],'channelId':CHANNEL_ID,'schedulingType':'automatic','mode':'shareNow','aiAssisted':True,'assets':[{'image':{'url':r['image_url'],'metadata':{'altText':r['image_alt_text']}}}],'needsApproval':False}}).get('createPost',{}).get('post')
    if not post or post.get('channelId')!=CHANNEL_ID:raise SystemExit('Creation uncertain; never resend')
    save({'campaign_id':r['campaign_id'],'outcome':'accepted','post':post})
    for _ in range(6):
        if post.get('status')=='sent' and post.get('externalLink') and any(str(a.get('mimeType','')).startswith('image/') for a in post.get('assets',[])):break
        time.sleep(8)
        post=next((p for p in history(call,org) if p['id']==post['id']),post)
    ok=post.get('status')=='sent' and post.get('externalLink') and any(str(a.get('mimeType','')).startswith('image/') for a in post.get('assets',[]))
    save({'campaign_id':r['campaign_id'],'outcome':'published' if ok else 'accepted_only','post':post})
    if not ok:raise SystemExit('Publication unconfirmed; reconcile without resend')
    print(json.dumps({'status':post['status'],'externalLink':post['externalLink'],'image':True}))
if __name__=='__main__':main()
