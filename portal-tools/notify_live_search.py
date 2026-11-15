"""Notify IndexNow of live, crawlable portal URLs; acceptance is not indexing."""
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
from prepare_live import ORIGIN, ROOT

def read(url):
    with urlopen(Request(url,headers={'User-Agent':'Monoyori-Discovery/1.0'}),timeout=35) as r:
        return r.read()

def main():
    robots=read(ORIGIN+'/robots.txt').decode()
    if 'Disallow: /' in robots:raise SystemExit('Crawling remains blocked')
    key=json.loads((ROOT/'portal-tools/indexnow_config.json').read_text())['key']
    if read(ORIGIN+'/'+key+'.txt').decode().strip()!=key:raise SystemExit('Ownership file mismatch')
    urls=[x.text for x in ET.fromstring(read(ORIGIN+'/sitemap.xml')).iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    if not urls or any(not u.startswith(ORIGIN+'/') for u in urls):raise SystemExit('Unexpected sitemap origin')
    payload={'host':urlsplit(ORIGIN).hostname,'key':key,'keyLocation':ORIGIN+'/'+key+'.txt','urlList':urls}
    req=Request('https://api.indexnow.org/indexnow',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urlopen(req,timeout=45) as r:
        if r.status not in (200,202):raise SystemExit('Notification not accepted')
        receipt={'origin':ORIGIN,'submitted_urls':len(urls),'http_status':r.status,'indexed_urls':None,'note':'Submission only. Search inclusion and traffic are not confirmed.'}
    Path('review-proof').mkdir(exist_ok=True)
    Path('review-proof/search-submission.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt))

if __name__=='__main__':main()
