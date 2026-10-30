#!/usr/bin/env python3
"""Offline regression checks for the three public portals (stdlib only)."""
import importlib.util
import ast
import sys
sys.dont_write_bytecode = True
import json
import re
import subprocess
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("refresh_portals",ROOT/"portal-tools"/"refresh_portals.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def check(cond,message):
    if not cond:
        raise AssertionError(message)

def main():
    required=["deals/index.html","events/index.html","products/index.html"]
    counts={}
    for name in required:
        data=(ROOT/name).read_text(encoding="utf-8")
        check("<html lang=\"ja\">" in data and "</html>" in data,name+" invalid document")
        check("G-J5ZDLF30CS" in data,name+" missing analytics")
        check("<link rel=\"canonical\"" in data,name+" missing canonical")
        meta=module.read_data(data)
        rows=meta["items"]
        check(len(rows)>0,name+" has no editorial listings")
        ids=[x.get("id") for x in rows]
        check(len(ids)==len(set(ids)),name+" duplicate IDs")
        for row in rows:
            check(all(row.get(k) for k in ("id","title","category","description","url")),name+" missing required card data")
            check(urlparse(row["url"]).scheme=="https",name+" insecure URL")
            if name.startswith("events"):
                check(row.get("prefecture") and row.get("start") and row.get("end"),name+" missing event date")
                check(date.fromisoformat(row["start"])<=date.fromisoformat(row["end"]),name+" invalid date range")
            if "end" in row and row["end"]:
                date.fromisoformat(row["end"])
        generated=module.regenerate(data,"2026-10-30")
        check("<div class=\"grid\" id=\"cards\">" in generated,name+" missing card grid after refresh")
        # JSON data is preserved so client filtering remains possible.
        check(len(module.read_data(generated)["items"])==len(rows),name+" lost data during generation")
        counts[name]=len(rows)
    for name in ("portal-assets/rakuten-feed.json","portal-assets/a8-approved.json"):
        feed=json.loads((ROOT/name).read_text(encoding="utf-8"))
        check(isinstance(feed.get("items"),list),name+" invalid affiliate feed")
    script=(ROOT/"portal-assets"/"app.js").read_text(encoding="utf-8")
    check(all(x in script for x in ("今週末","来月開催","portal_outbound_click","expires_at")), "Missing key filters, tracking or expiration")
    subprocess.run(["node","--check",str(ROOT/"portal-assets"/"app.js")],check=True)
    for script in ("refresh_portals.py","refresh_rakuten.py"):
        ast.parse((ROOT/"portal-tools"/script).read_text(encoding="utf-8"))
    print("PASS:",counts,"47 prefecture options and expiration checks")

if __name__=="__main__":
    main()
