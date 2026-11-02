#!/usr/bin/env python3
"""Run the actual sitemap writers against noindex and active-page fixtures.

The article module is compiled from its functions, without constructing an API
client, generating articles or consuming LLM credits.
"""
import ast
import contextlib
import io
import json
import os
import sys
import tempfile
import textwrap
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sitemap_pages import site_sitemap_pages

BASE='https://sho-support.github.io/ai-trend-blog'
NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}


class SitemapWriters(unittest.TestCase):
    def setUp(self):
        before=Path.cwd();temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup);self.addCleanup(os.chdir,before)
        os.chdir(temporary.name)
        fixtures={'index.html':'<h1>ニュース</h1>','archive.html':'<h1>過去記事</h1>',
                  'category/test.html':'<h1>開発</h1>','products/index.html':'<h1>商品</h1>',
                  'products/items/live.html':'<h1>掲載中の商品</h1>',
                  'products/items/retired.html':'<meta content="noindex,follow" name="robots"><h1>終了</h1>',
                  'products/search.html':"<META CONTENT='NOINDEX, FOLLOW' NAME='ROBOTS'><h1>検索</h1>",
                  'products/blocked.html':'<h1>非公開の棚</h1>',
                  'deals/index.html':'<h1>セール</h1>'}
        for name,body in fixtures.items():
            path=Path(name);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)
        path=Path('portal-assets/discovery-manifest.json');path.parent.mkdir()
        path.write_text(json.dumps({'pages':[
            {'url':BASE+'/products/items/live.html','indexable':True,'lastmod':'2026-10-31'},
            {'url':BASE+'/products/blocked.html','indexable':False,'lastmod':'2026-10-31'}]}))

    def namespace(self):
        return {'datetime':datetime,'timezone':timezone,'timedelta':timedelta,'JST':timezone(timedelta(hours=9)),
                'Path':Path,'Element':ET.Element,'SubElement':ET.SubElement,'ElementTree':ET.ElementTree,'indent':ET.indent,
                'SITE_BASE_URL':BASE,'INDEX_FILE':Path('index.html'),'SITE_SITEMAP_FILE':Path('site-sitemap.xml'),
                'ARTICLES_SITEMAP_FILE':Path('articles-sitemap.xml'),'SITEMAP_INDEX_FILE':Path('sitemap-index.xml'),
                'SITEMAP_FILE':Path('sitemap.xml'),'ARTICLE_DIR':Path('articles'),
                'CATEGORIES':[{'slug':'test'}],'site_sitemap_pages':site_sitemap_pages}

    def assert_inventory(self):
        rows={node.findtext('s:loc',namespaces=NS):node.findtext('s:lastmod',namespaces=NS)
              for node in ET.parse('site-sitemap.xml').getroot()}
        for relative in ('products/items/retired.html','products/search.html','products/blocked.html'):
            self.assertFalse(BASE+'/'+relative in rows,relative+' must not be submitted')
        for relative in ('products/','products/items/live.html','deals/','archive.html','category/test.html'):
            self.assertTrue(BASE+'/'+relative in rows,relative+' must stay discoverable')
        self.assertEqual(rows[BASE+'/products/items/live.html'],'2026-10-31')

    def test_article_refresh_keeps_noindex_exclusions_and_product_dates(self):
        tree=ast.parse((ROOT/'generate_article.py').read_text())
        functions=[node for node in tree.body if isinstance(node,ast.FunctionDef)
                   and node.name in ('history_date_map','_write_xml','generate_sitemap')]
        namespace=self.namespace()
        exec(compile(ast.Module(body=functions,type_ignores=[]),'generate_article.py','exec'),namespace)
        with contextlib.redirect_stdout(io.StringIO()):namespace['generate_sitemap']([])
        self.assert_inventory()

    def test_internal_link_refresh_keeps_all_active_product_routes(self):
        source=(ROOT/'.github/workflows/internal-links.yml').read_text()
        script=textwrap.dedent(source.split("python - <<'PY'\n",1)[1].split('\n          PY',1)[0])
        marker=script.index('# site-sitemap.xml に archive/category を追加')
        block=script[script.index('today =',marker):]
        with contextlib.redirect_stdout(io.StringIO()):exec(compile(block,'internal-links.yml','exec'),self.namespace())
        self.assert_inventory()


if __name__=='__main__':unittest.main()
