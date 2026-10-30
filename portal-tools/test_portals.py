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
    guides = (
        "okashi-matome.html", "okome-5kg.html",
        "mobile-battery-monitors.html", "nichiyohin-matome.html",
        "sneakers.html", "skincare.html", "pet-supplies.html",
    )
    for filename in guides:
        page = (ROOT/"products"/filename).read_text(encoding="utf-8")
        check('window.GUIDE_CATEGORY=' in page, filename+" missing category")
        check('portal-assets/guide.js' in page, filename+" missing official feed script")
        check('rel="canonical"' in page, filename+" missing SEO canonical")
        check("PR｜広告" in page, filename+" missing visible advertising disclosure")
    home = (ROOT/"products"/"index.html").read_text(encoding="utf-8")
    check(all(filename in home for filename in guides), "product home missing guide links")
    affiliate_feed = json.loads((ROOT/"portal-assets"/"rakuten-feed.json").read_text(encoding="utf-8"))
    for item in affiliate_feed["items"]:
        check(item.get("approved") is True, "unapproved Rakuten item in public feed")
        check(item.get("expires_at"), "Rakuten price data without expiry")
        check(urlparse(item.get("url") or "").scheme == "https", "Rakuten item URL not HTTPS")
        if item.get("affiliate"):
            check("rakuten.co.jp" in urlparse(item["url"]).netloc, "Non-Rakuten affiliate destination")
    # The API mandates its exact, unmodified attribution snippet on pages
    # that show Rakuten Web Service product or hotel data.
    for source in ("deals/index.html", "products/index.html", "events/index.html"):
        body = (ROOT/source).read_text(encoding="utf-8")
        check("Supported by Rakuten Developers</a>" in body, source+" missing official API attribution")
    event_index = (ROOT/"events/index.html").read_text(encoding="utf-8")
    check("portal-assets/travel.js" in event_index, "event stay widget missing")
    travel_feed = json.loads((ROOT/"portal-assets/travel-feed.json").read_text(encoding="utf-8"))
    check(isinstance(travel_feed.get("items"), list), "invalid Rakuten Travel feed")
    for hotel in travel_feed["items"]:
        check(hotel.get("affiliate") is True, "unapproved hotel listing")
        check(hotel.get("expires_at"), "hotel listing has no expiry")
        check(hotel.get("prefecture") and hotel.get("city"), "hotel location missing")
        check(urlparse(hotel["url"]).scheme == "https", "insecure hotel referral link")
    script=(ROOT/"portal-assets"/"app.js").read_text(encoding="utf-8")
    check(all(x in script for x in ("今週末","来月開催","portal_outbound_click","expires_at")), "Missing key filters, tracking or expiration")
    subprocess.run(["node","--check",str(ROOT/"portal-assets"/"app.js")],check=True)
    subprocess.run(["node","--check",str(ROOT/"portal-assets"/"guide.js")],check=True)
    subprocess.run(["node","--check",str(ROOT/"portal-assets"/"travel.js")],check=True)
    for script in ("refresh_portals.py","refresh_rakuten.py","refresh_travel.py","build_commercial_site.py"):
        ast.parse((ROOT/"portal-tools"/script).read_text(encoding="utf-8"))
    print("PASS:",counts,"47 prefecture options and expiration checks")

if __name__=="__main__":
    main()
