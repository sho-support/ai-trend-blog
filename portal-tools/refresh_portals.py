#!/usr/bin/env python3
"""Refresh the compact portals from their maintained data, without an LLM."""
import json
import re
from datetime import datetime, timedelta, timezone
from build_storefront import ROOT, main
JST=timezone(timedelta(hours=9))

def read_data(page):
    match=re.search(r'window\.PORTAL_DATA=(\{[\s\S]*?\});</script>',page)
    if not match: raise ValueError('Missing PORTAL_DATA')
    return json.loads(match.group(1))

def active(item,today):
    return isinstance(item,dict) and (not item.get('end') or item['end']>=today)

if __name__=='__main__':main()
