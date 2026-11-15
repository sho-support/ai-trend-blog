"""Promote the registered Cloudflare portal without changing its public origin."""
import json
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
ORIGIN='https://sho-monoyori-review.zodiac-suu.workers.dev'

def merge_feed(fresh, editorial):
    old={x['id']:x for x in editorial['items']}
    for row in fresh['items']:
        previous=old.get(row['id'],{})
        if not row.get('review_average') and previous.get('review_average'):
            # A rating and its denominator/date are one snapshot, never mix dates.
            for key in ('review_average','review_count','rating_verified'):
                if key in previous: row[key]=previous[key]
            row['rating_verified']=previous.get('rating_verified') or previous.get('verified')
    # Manually checked items survive only until their original expiry.
    ids={x['id'] for x in fresh['items']}
    for row in editorial['items']:
        if row['id'] not in ids and row.get('verification_method')=='merchant_page':
            if datetime.fromisoformat(row['expires_at'])>datetime.now(timezone.utc):
                fresh['items'].append(row)
    return fresh

def main():
    registration=json.loads((ROOT/'growth/live-registration.json').read_text())
    if registration.get('origin')!=ORIGIN or registration.get('rakuten_registered') is not True:
        raise SystemExit('Confirmed registration for this exact origin is required')
    root=ROOT/'dist'
    for path in root.rglob('*.html'):
        text=path.read_text()
        # Workers redirects .html to its extensionless canonical route.
        text=re.sub(re.escape(ORIGIN)+r'(/[^"\s<>]*?)\.html',ORIGIN+r'\1',text)
        path.write_text(text)
    sitemap=root/'sitemap.xml'
    sitemap.write_text(sitemap.read_text().replace('.html</loc>','</loc>'))
    (root/'_headers').write_text('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n/portal-assets/*.json\n  Cache-Control: public, max-age=300\n')
    # A8 and travel were registered against the old site only. Do not enable
    # those placements on the new origin by merely reusing a stale approval.
    assert not any('review-mode.js' in p.read_text() for p in root.rglob('*.html'))
    config={'name':'sho-monoyori-review','compatibility_date':'2026-11-14','workers_dev':True,'preview_urls':False,'assets':{'directory':'./dist','html_handling':'auto-trailing-slash','not_found_handling':'404-page'}}
    (ROOT/'wrangler.monoyori.json').write_text(json.dumps(config))
    print('Registered Rakuten portal: purchase links, GA4 and search crawling enabled.')

if __name__=='__main__':main()
