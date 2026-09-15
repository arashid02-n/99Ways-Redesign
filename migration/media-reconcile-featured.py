#!/usr/bin/env python3
"""Reconcile the media map so featured images reuse the existing EmDash media
items referenced by live posts/pages (the seed-time uploads), and delete the
duplicate copies created by migrate-media.py for those wp featured media ids.

Alt/caption that WordPress carries for featured media is re-applied onto the
kept item. Non-featured migrated media are unaffected.

Inputs (live dumps, not committed):
  /tmp/99ways-tmp/posts_live.json, /tmp/99ways-tmp/pages_live.json

Usage:
  EMDASH_TOKEN=ec_pat_* python3 migration/media-reconcile-featured.py
"""
import json
import os
import sys

import requests

BASE = "http://localhost:4321"
TOKEN = os.environ.get("EMDASH_TOKEN")
if not TOKEN:
    sys.exit("EMDASH_TOKEN env var is required")
H = {"Authorization": f"Bearer {TOKEN}", "X-EmDash-Request": "1"}
MAP = "migration/wordpress-source/media-map.json"


def main():
    mapping = json.load(open(MAP))
    wp_posts = {p["slug"]: p for p in json.load(open("migration/wordpress-source/posts.json"))}
    wp_pages = {p["slug"]: p for p in json.load(open("migration/wordpress-source/pages.json"))}

    # wp featured id -> existing emdash {id, storageKey, url, alt}
    existing = {}
    for dump, wpsrc in (("/tmp/99ways-tmp/posts_live.json", wp_posts), ("/tmp/99ways-tmp/pages_live.json", wp_pages)):
        live = json.load(open(dump))["data"]["items"]
        for it in live:
            wfit = wpsrc.get(it["slug"], {}).get("featured_media")
            fim = it["data"].get("featured_image")
            if wfit and fim and isinstance(fim, dict) and fim.get("id"):
                existing[str(wfit)] = {
                    "id": fim["id"],
                    "storageKey": (fim.get("meta") or {}).get("storageKey"),
                    "url": f'/_emdash/api/media/file/{(fim.get("meta") or {}).get("storageKey")}',
                    "alt": fim.get("alt"),
                }

    # Apply WP alt/caption onto kept featured items; delete new duplicates.
    deleted = []
    for wid, fmt in existing.items():
        ent = mapping.get(wid)
        if not ent or ent.get("status") != "migrated":
            continue
        new_id = ent.get("id")
        keep = fmt["id"]
        if new_id == keep:
            continue
        # backfill alt/caption from wordpress
        wpa = json.load(open("migration/wordpress-source/media.json"))
        src = next((x for x in wpa if str(x["id"]) == wid), None)
        alt = fmt["alt"]
        caption = ((src.get("caption") or {}).get("rendered") or "").strip() if src else None
        body = {k: v for k, v in {"alt": alt, "caption": caption}.items() if v}
        if body:
            requests.put(f"{BASE}/_emdash/api/media/{keep}", headers=H, json=body, timeout=60)
        # delete the new duplicate
        r = requests.delete(f"{BASE}/_emdash/api/media/{new_id}", headers=H, timeout=60)
        deleted.append((wid, new_id, keep, r.status_code))
        ent["id"] = keep
        ent["storageKey"] = fmt["storageKey"]
        ent["url"] = fmt["url"]
        ent["reuse"] = "existing-featured"

    json.dump(mapping, open(MAP, "w"), ensure_ascii=False, indent=2)
    print(f"reused existing ids for {len([d for d in deleted if d[3] in (200,204)])} featured media; delete statuses:")
    from collections import Counter
    print(Counter(d[3] for d in deleted))


if __name__ == "__main__":
    main()