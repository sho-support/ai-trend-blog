#!/usr/bin/env python3
"""Notify IndexNow of genuine catalogue changes; never claim URLs are indexed."""
import argparse
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, unquote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://sho-support.github.io/ai-trend-blog/'
ENDPOINT = 'https://api.indexnow.org/indexnow'
HEADERS = {'User-Agent': 'Monoyori-Discovery/1.0 (+https://sho-support.github.io/ai-trend-blog/deals/about.html)'}


def owned_url(url):
    parsed = urlsplit(url)
    return (parsed.scheme == 'https' and parsed.netloc == 'sho-support.github.io'
            and parsed.path.startswith('/ai-trend-blog/') and not parsed.query and not parsed.fragment
            and '..' not in unquote(parsed.path).split('/')
            and not parsed.username and not parsed.password)


def changes(pages, known):
    result = []
    seen = set()
    for row in pages:
        url = row['url']
        if not owned_url(url):
            raise ValueError('Discovery manifest contains a URL outside this site')
        if url in seen:
            raise ValueError('Duplicate discovery URL')
        seen.add(url)
        if known.get(url) != row['fingerprint']:
            result.append(row)
    return result


def get(url):
    with urlopen(Request(url, headers=HEADERS), timeout=25) as response:
        if response.status != 200:
            raise ValueError('Public resource is not available')
        return response.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    config = json.loads((ROOT/'portal-tools/indexnow_config.json').read_text())
    if not owned_url(config['keyLocation']):
        raise SystemExit('Invalid verification file location')
    state = json.loads(args.state.read_text()) if args.state.exists() else {}
    manifest = json.loads((ROOT/'portal-assets/discovery-manifest.json').read_text())
    if not args.dry_run:
        # Pages deployment can finish after the catalogue workflow. Wait for the
        # exact public build rather than sending URLs that are not live yet.
        for attempt in range(12):
            try:
                key_ok = get(config['keyLocation']).decode().strip() == config['key']
                remote = json.loads(get(BASE+'portal-assets/discovery-manifest.json'))
                html_ready=b'window.CATALOG_INITIAL=' in get(BASE+'products/')
                if key_ok and remote == manifest and html_ready:
                    break
            except (HTTPError, URLError, TimeoutError, ValueError):
                pass
            if attempt == 11:
                raise SystemExit('Public verification file or catalogue build is not ready; no notification sent')
            time.sleep(5)
    pending = changes(manifest['pages'], state)
    receipt = {'submitted_urls': 0, 'http_statuses': [], 'indexed_urls': None,
               'key_validation_pending': False, 'dry_run': args.dry_run}
    if args.dry_run:
        receipt['candidate_urls'] = len(pending)
    else:
        for offset in range(0, len(pending), 500):
            batch = pending[offset:offset+500]
            data = json.dumps({'host': 'sho-support.github.io', 'key': config['key'],
                               'keyLocation': config['keyLocation'],
                               'urlList': [x['url'] for x in batch]}).encode()
            request = Request(ENDPOINT, data=data,
                              headers={**HEADERS, 'Content-Type': 'application/json; charset=utf-8'}, method='POST')
            with urlopen(request, timeout=45) as response:
                status = response.status
            if status not in (200, 202):
                raise SystemExit('IndexNow did not accept this batch')
            state.update({x['url']: x['fingerprint'] for x in batch})
            args.state.parent.mkdir(parents=True, exist_ok=True)
            args.state.write_text(json.dumps(state, sort_keys=True)+'\n')
            receipt['submitted_urls'] += len(batch)
            receipt['http_statuses'].append(status)
            receipt['key_validation_pending'] |= status == 202
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))
    print('Submission receipt only. Search indexing and traffic are not confirmed by this response.')


if __name__ == '__main__':
    main()
