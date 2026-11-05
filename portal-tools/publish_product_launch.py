#!/usr/bin/env python3
"""Publish a reviewed product notice only on a separate commerce X channel.

No LLM calls, no new account, no queue changes, no mutation retries. The request
file is a one-shot instruction; a recorded/ambiguous attempt cannot send again.
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

from product_text import approved_a8
from storefront_seo import live

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://sho-support.github.io/ai-trend-blog'
POLICY = json.loads((ROOT/'growth/channel-policy.json').read_text())
HANDLE = POLICY['products'].get('handle')
CHANNEL_ID = POLICY['products'].get('channel_id')
RECEIPT = ROOT/'growth/x-launch-receipt.json'
FIELDS = 'id text status dueAt sentAt externalLink channelId assets { id mimeType }'


def registered_link(request, item, social_links=None):
    if social_links is None:
        social_links = json.loads((ROOT/'growth/product-social-links.json').read_text())['links']
    return next((x for x in social_links if x.get('product_id') == item['id']
                 and x.get('handle') == HANDLE and x.get('url') == request.get('url')), None)


def reviewed_image(request, item, social_link=None):
    url = request.get('image_url')
    if not url:
        if request.get('require_image') is True or item.get('source') == 'rakuten':
            raise ValueError('This product notice requires its reviewed product photograph.')
        return None
    parsed = urlsplit(url)
    alt = request.get('image_alt_text', '')
    # Permission to display an API image on our website is not SNS image permission.
    material = social_link if item.get('source') == 'rakuten' else item
    expected = material.get('image_url') if item.get('source') == 'rakuten' and material else (material or {}).get('image')
    if (not material or material.get('image_authorized') is not True or url != expected
            or (item.get('source') == 'rakuten' and material.get('image_source') != 'rakuten_affiliate_link_builder')
            or parsed.scheme != 'https' or not parsed.hostname or parsed.fragment or parsed.username or parsed.password
            or not isinstance(alt, str) or not alt.strip() or len(alt) > 1000):
        raise ValueError('Use the exact authorized product image and a short image description.')
    return {'image': {'url': url, 'metadata': {'altText': alt}}}


def validate_rakuten_notice(request, item, link):
    destination = parse_qs(urlsplit(item['url']).query).get('pc', [])
    target = urlsplit(link.get('destination_url', ''))
    if (urlsplit(request['url']).hostname != 'a.r10.to'
            or link.get('retrieval_method') != 'rakuten_affiliate_link_builder'
            or link.get('link_type') != 'short_url' or link.get('price_navi') is not False
            or link.get('site_url') != 'https://x.com/'+HANDLE
            or link.get('redirect_verified') is not True or len(destination) != 1
            or link.get('destination_url') != destination[0]
            or target.scheme != 'https' or target.hostname != 'item.rakuten.co.jp'
            or target.username or target.password or target.fragment):
        raise ValueError('Register this X profile and obtain its exact Rakuten product link from the link builder.')
    price = request.get('price_yen')
    day = request.get('price_verified_date', '')
    try:
        date = datetime.strptime(day, '%Y-%m-%d')
    except (TypeError, ValueError):
        raise ValueError('A reviewed Rakuten price date is required.') from None
    text = request.get('text', '')
    if (type(price) is not int or price != item.get('price_yen') or day != item.get('verified')
            or f'{price:,}円' not in text or f'{date.month}月{date.day}日確認' not in text
            or '楽天市場' not in text):
        raise ValueError('The Rakuten price or date changed; review the copy before sending.')


def catalog_path(product_id):
    if isinstance(product_id, str):
        for prefix, name in (('a8-', 'a8-approved.json'), ('rakuten-', 'rakuten-feed.json')):
            if product_id.startswith(prefix):
                return 'portal-assets/'+name
    raise ValueError('Unknown product catalogue; no fallback is allowed.')


def image_confirmed(request, post):
    return not request.get('image_url') or any(
        str(asset.get('mimeType', '')).startswith('image/')
        for asset in ((post or {}).get('assets') or [])
    )


def read_json(url):
    with urlopen(Request(url, headers={'User-Agent': 'MonoyoriLaunch/1.0'}), timeout=25) as response:
        return json.load(response)


def validate(request, items, now=None, social_links=None):
    now = now or datetime.now(timezone.utc)
    if not HANDLE or not CHANNEL_ID or HANDLE.lower() == POLICY['ai']['handle'].lower() or CHANNEL_ID == POLICY['ai']['channel_id']:
        raise ValueError('Connect a separate product X account before publishing a product notice.')
    if request.get('channel_id') != CHANNEL_ID or request.get('handle') != HANDLE:
        raise ValueError('The request must name the verified product X channel.')
    if request.get('publish_now') is not True:
        raise ValueError('This request is not enabled for one immediate notice.')
    campaign = request.get('campaign_id', '')
    if not re.fullmatch(r'monoyori_[a-z0-9_]+', campaign):
        raise ValueError('Invalid campaign identifier.')
    item = next((x for x in items if x.get('id') == request.get('product_id')), None)
    if (not item or item.get('source') not in ('a8', 'rakuten')
            or not (approved_a8(item, now) if item.get('source') == 'a8' else live(item, now))):
        raise ValueError('The advertised product is no longer approved and current.')
    deadline = datetime.fromisoformat(request['expires_at'].replace('Z', '+00:00'))
    source_deadline = datetime.fromisoformat(item['expires_at'].replace('Z', '+00:00'))
    if deadline.tzinfo is None or not now < deadline <= source_deadline:
        raise ValueError('The notice must expire by the existing product review deadline.')
    url = request.get('url', '')
    parsed = urlsplit(url)
    link = registered_link(request, item, social_links)
    if (not link or link.get('placement') != 'x' or link.get('site_registered') is not True
            or link.get('program_allowed') is not True or link.get('provider') != item.get('source')
            or not link.get('checked_at') or parsed.scheme != 'https' or not parsed.hostname
            or parsed.hostname == 'sho-support.github.io' or parsed.fragment or parsed.username or parsed.password):
        raise ValueError('Use the exact verified X affiliate link that leads to the official shop.')
    link_deadline = datetime.fromisoformat(link['expires_at'].replace('Z','+00:00'))
    checked = datetime.fromisoformat(link['checked_at'].replace('Z','+00:00'))
    if link_deadline.tzinfo is None or checked.tzinfo is None or not checked <= now < link_deadline or deadline > link_deadline:
        raise ValueError('The social affiliate link review is no longer current.')
    if item['source'] == 'rakuten':
        validate_rakuten_notice(request, item, link)
    reviewed_image(request, item, link)
    text = request.get('text', '')
    urls = re.findall(r'https?://\S+', text)
    if not text.startswith('【PR】') or urls != [url]:
        raise ValueError('A single disclosed PR notice with its reviewed URL is required.')
    # X treats a URL as 23 weighted characters; Japanese is counted as two.
    plain = text.replace(url, '')
    if sum(1 if ord(c) <= 0x10ff else 2 for c in plain) + 23 > 270:
        raise ValueError('The reviewed notice exceeds the X length limit.')
    return item


def graphql_client(token):
    def call(query, variables=None):
        payload = json.dumps({'query':query, 'variables':variables or {}}).encode()
        req = Request('https://api.buffer.com', data=payload, method='POST',
                      headers={'Authorization':'Bearer '+token, 'Content-Type':'application/json'})
        try:
            with urlopen(req, timeout=30) as response:
                body = json.load(response)
        except Exception:
            # Never echo request headers, credentials or a credential-bearing exception.
            raise RuntimeError('Buffer request failed; do not automatically repeat a post mutation.') from None
        if body.get('errors'):
            message = '; '.join(str(x.get('message', 'API error')) for x in body['errors'])
            raise RuntimeError(message.replace(token, '[redacted]')[:600])
        return body.get('data') or {}
    return call


def target_organization(call):
    account = call('query { account { organizations { id } } }')
    for org in account.get('account', {}).get('organizations', []):
        data = call('query($id:OrganizationId!) { channels(input:{organizationId:$id}) '
                    '{ id name displayName service externalLink isDisconnected isLocked } }', {'id':org['id']})
        for channel in data.get('channels', []):
            if channel.get('id') != CHANNEL_ID:
                continue
            link = urlsplit(channel.get('externalLink') or '')
            if (channel.get('service') != 'twitter' or channel.get('isDisconnected')
                    or channel.get('isLocked') or link.scheme != 'https'
                    or link.hostname not in ('twitter.com', 'x.com', 'www.twitter.com', 'www.x.com')
                    or link.path.strip('/').lower() != HANDLE.lower()):
                raise ValueError('The exact product channel is not currently available.')
            return org['id']
    raise ValueError('The exact product X channel was not found; no fallback channel is allowed.')


def find_post(call, org, request):
    after = None
    for _ in range(6):
        suffix = ',after:'+json.dumps(after) if after else ''
        query = ('query($input:PostsInput!) { posts(first:50'+suffix+',input:$input) '
                 '{ edges { node { '+FIELDS+' } } pageInfo { hasNextPage endCursor } } }')
        result = call(query, {'input':{'organizationId':org,
                      'filter':{'channelIds':[CHANNEL_ID], 'startDate':request['created_at']},
                      'sort':[{'field':'createdAt', 'direction':'desc'}]}}).get('posts', {})
        for edge in result.get('edges', []):
            post = edge['node']
            if request['url'] in (post.get('text') or ''):
                if post.get('channelId') != CHANNEL_ID:
                    raise ValueError('Unexpected destination in Buffer history.')
                return post
        page = result.get('pageInfo', {})
        if not page.get('hasNextPage'):
            return None
        after = page.get('endCursor')
        if not after:
            raise ValueError('Could not finish checking for an earlier notice.')
    raise ValueError('History scan was incomplete; refusing a possible duplicate.')


def receipt_for(request, post, outcome):
    link = post.get('externalLink') if post else None
    if link:
        u = urlsplit(link)
        if u.scheme != 'https' or u.hostname not in ('x.com', 'twitter.com', 'www.x.com', 'www.twitter.com'):
            link = None
    return {'campaign_id':request['campaign_id'], 'channel_handle':HANDLE,
            'product_id':request['product_id'], 'landing_url':request['url'],
            'post_id':post.get('id') if post else None,
            'status':post.get('status') if post else 'submission_unknown',
            'outcome':outcome, 'external_url':link,
            'sent_at':post.get('sentAt') if post else None,
            'image_url':request.get('image_url'),
            'image_confirmed':image_confirmed(request, post),
            'asset_count':len((post or {}).get('assets') or []),
            'checked_at':datetime.now(timezone.utc).isoformat()}


def save_receipt(receipt, target=RECEIPT):
    campaign = receipt.get('campaign_id', '')
    if not re.fullmatch(r'monoyori_[a-z0-9_]+', campaign):
        raise ValueError('Invalid receipt campaign identifier.')
    archive = target.parent/'x-launch-receipts'/(campaign+'.json')
    archive.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(receipt, ensure_ascii=False, indent=2)+'\n'
    archive.write_text(body)
    target.write_text(body)


def launch(request, items, call, previous=None, write=lambda receipt:None, pause=time.sleep, social_links=None):
    item = validate(request, items, social_links=social_links)
    org = target_organization(call)
    existing = find_post(call, org, request)
    if existing:
        receipt = receipt_for(request, existing, 'existing_notice' if image_confirmed(request, existing) else 'image_unconfirmed')
        write(receipt)
        if not image_confirmed(request, existing):
            raise RuntimeError('The existing notice has no confirmed product image. Check it in Buffer; do not post again.')
        return receipt
    if previous and previous.get('campaign_id') == request['campaign_id']:
        raise RuntimeError('An earlier attempt is recorded. Reconcile it in Buffer instead of posting again.')
    # Persist the claim before making the only write request, even if its response is lost.
    write(receipt_for(request, None, 'attempt_started'))
    asset = reviewed_image(request, item, registered_link(request, item, social_links))
    variables = {'input':{'text':request['text'], 'channelId':CHANNEL_ID,
                 'schedulingType':'automatic', 'mode':'shareNow', 'aiAssisted':True,
                 'assets':[asset] if asset else [], 'needsApproval':False}}
    result = call('mutation($input:CreatePostInput!) { createPost(input:$input) '
                  '{ ... on PostActionSuccess { post { '+FIELDS+' } } ... on MutationError { message } } }', variables)
    action = result.get('createPost', {})
    post = action.get('post')
    if not post or not post.get('id') or post.get('channelId') != CHANNEL_ID:
        raise RuntimeError('Buffer did not confirm a post on the selected channel: '+str(action.get('message') or 'unknown response')[:400])
    receipt = receipt_for(request, post, 'accepted')
    write(receipt)
    for _ in range(4):
        if post.get('status') == 'sent' and post.get('externalLink') and image_confirmed(request, post):
            break
        pause(8)
        current = find_post(call, org, request)
        if current:
            post = current
    outcome = 'published' if post.get('status') == 'sent' else 'accepted_only'
    if not image_confirmed(request, post):
        outcome = 'image_unconfirmed'
    receipt = receipt_for(request, post, outcome)
    write(receipt)
    if outcome == 'image_unconfirmed':
        raise RuntimeError('Buffer has not confirmed the product image. Check the recorded post; do not post again.')
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--publish-now', action='store_true')
    args = parser.parse_args()
    if not POLICY['products'].get('enabled'):
        print('商品紹介用Xの準備待ち。AIアカウントへの商品PRは送信しません。')
        return
    request = json.loads((ROOT/'growth/x-launch.json').read_text())
    path = catalog_path(request.get('product_id'))
    items = json.loads((ROOT/path).read_text())['items']
    validate(request, items)
    if not args.publish_now:
        print(json.dumps({'mode':'validation_only', 'handle':HANDLE, 'text':request['text']}, ensure_ascii=False))
        return
    # Recheck the actual public advertisement before writing to Buffer.
    current_items = read_json(BASE+'/'+path)['items']
    current = validate(request, current_items)
    local = validate(request, items)
    if current['url'] != local['url']:
        raise ValueError('The public advertisement changed; review the notice again.')
    with urlopen(BASE+'/products/items/'+current['id']+'.html', timeout=25) as response:
        page = response.read().decode()
    if 'data-buy="'+current['id']+'"' not in page or 'noindex,follow' in page:
        raise ValueError('The advertised public product page is unavailable.')
    token = os.environ.get('BUFFER_API_KEY')
    if not token:
        raise RuntimeError('The existing Buffer credential is not configured.')
    archive = ROOT/'growth/x-launch-receipts'/(request['campaign_id']+'.json')
    prior_path = archive if archive.exists() else RECEIPT
    previous = json.loads(prior_path.read_text()) if prior_path.exists() else None
    def write(receipt):
        save_receipt(receipt)
    receipt = launch(request, current_items, graphql_client(token), previous, write)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(type(error).__name__+': '+str(error), file=sys.stderr)
        raise SystemExit(1)
