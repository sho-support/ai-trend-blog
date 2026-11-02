"""Shared page eligibility for the article and internal-link sitemap writers."""
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path


class Robots(HTMLParser):
    def __init__(self, source):
        super().__init__(); self.excluded=False; self.feed(source)

    def handle_starttag(self, tag, attrs):
        row={k.lower():v or '' for k,v in attrs}
        if tag.lower() == 'meta' and row.get('name','').lower() in ('robots','googlebot'):
            tokens=re.split(r'[,;\s]+',row.get('content','').lower())
            self.excluded |= any(x in tokens for x in ('noindex','none'))


def site_sitemap_pages(base, root=Path('.')):
    try:
        manifest=json.loads((root/'portal-assets/discovery-manifest.json').read_text())
        known={x['url']:x for x in manifest.get('pages',[])}
    except (OSError,ValueError,KeyError,TypeError):
        known={}
    try:
        ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
        previous={x.findtext('s:loc',namespaces=ns):x.findtext('s:lastmod',namespaces=ns)
                  for x in ET.parse(root/'site-sitemap.xml').getroot()}
    except (OSError,ET.ParseError):
        previous={}
    paths=[root/'archive.html']
    for section in ('deals','events','products','category'):
        paths.extend((root/section).rglob('*.html'))
    rows=[]
    for path in sorted(set(paths)):
        if not path.is_file():continue
        source=path.read_text(encoding='utf-8')
        if Robots(source).excluded:continue
        relative=path.relative_to(root).as_posix()
        if relative.endswith('/index.html'):relative=relative[:-10]
        url=base.rstrip('/')+'/'+relative
        row=known.get(url,{})
        if row.get('indexable') is False:continue
        explicit=re.search(r'"dateModified"\s*:\s*"(\d{4}-\d{2}-\d{2})"',source)
        stamp=row.get('lastmod') or (explicit.group(1) if explicit else previous.get(url))
        rows.append({'url':url,'lastmod':stamp if stamp and re.fullmatch(r'\d{4}-\d{2}-\d{2}',stamp) else None})
    return rows
