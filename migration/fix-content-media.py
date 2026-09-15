#!/usr/bin/env python3
"""Rewrite inline image references in live posts/pages from the read-only
WordPress host to local EmDash media URLs.

Walks every Portable Text `image` block whose `asset.url` points at
99ways.instawp.dev/wp-content/uploads/..., resolves the WordPress size-suffixed
variant to the base media file via migration/wordpress-source/media-map.json,
and stores the local /_emdash/api/media/file/<storageKey> URL. Then re-publishes
each changed item (preserving its original published_at).

Non /uploads/ URLs (plugin/theme assets) are left untouched and counted.

Usage:
  EMDASH_TOKEN=ec_pat_* python3 migration/fix-content-media.py
"""
import json
import os
import re
import sys

import requests

BASE = "http://localhost:4321"
TOKEN = os.environ.get("EMDASH_TOKEN")
if not TOKEN:
    sys.exit("EMDASH_TOKEN env var is required")
H = {"Authorization": f"Bearer {TOKEN}", "X-EmDash-Request": "1"}
MAP = json.load(open("migration/wordpress-source/media-map.json"))

EXACT = {
    (v["folder"], v["basename"]): v["url"]
    for v in MAP.values()
    if v.get("status") == "migrated" and v.get("folder") and v.get("basename")
}
BY_BASE: dict[str, list[str]] = {}
for v in MAP.values():
    if v.get("status") == "migrated" and v.get("basename"):
        BY_BASE.setdefault(v["basename"], []).append(v["url"])
SUFFIX = re.compile(r"-\d+x\d+(?=\.[A-Za-z0-9]+$)")


def resolve(url):
    if "wp-content/uploads/" not in url:
        return None  # not an uploads URL; leave untouched
    rel = url.split("wp-content/uploads/", 1)[-1]
    folder, fname = rel.rsplit("/", 1)
    stem = SUFFIX.sub("", fname)
    basename = stem.rsplit(".", 1)[0]
    # 1. exact folder + basename
    hit = EXACT.get((folder, basename))
    if hit:
        return hit
    # 2. unambiguous basename across any folder
    cands = BY_BASE.get(basename, [])
    if len(cands) == 1:
        return cands[0]
    # 3. wordpress "-scaled" style re-uploads
    alt = set()
    for bname, urls in BY_BASE.items():
        if bname == basename + "-scaled" or basename == bname + "-scaled":
            alt.update(urls)
    if len(alt) == 1:
        return next(iter(alt))
    return "MISS"


def rewrite_content(content):
    changed = 0
    misses = 0
    other = 0

    def walk(node):
        nonlocal changed, misses, other
        if isinstance(node, dict):
            asset = node.get("asset")
            if isinstance(asset, dict) and isinstance(asset.get("url"), str):
                url = asset["url"]
                new_url = resolve(url)
                if new_url is None:
                    other += 1
                elif new_url == "MISS":
                    misses += 1
                else:
                    asset["url"] = new_url
                    changed += 1
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(content)
    return content, changed, misses, other


def main():
    items = []
    for dump, collection in (
        ("/tmp/99ways-tmp/posts_live.json", "posts"),
        ("/tmp/99ways-tmp/pages_live.json", "pages"),
    ):
        d = json.load(open(dump))
        for it in d["data"]["items"]:
            items.append((collection, it["slug"] if it.get("slug") else it["id"]))

    total_changed = total_misses = total_other = 0
    updated = []
    for collection, ident in sorted(items):
        r = requests.get(f"{BASE}/_emdash/api/content/{collection}/{ident}?draft=false", headers=H, timeout=60)
        if r.status_code != 200:
            print(f"GET fail {collection}/{ident}: {r.status_code}")
            continue
        body = r.json()["data"]
        item = body["item"]
        rev = body["_rev"]
        content = item["data"].get("content")
        new_content, changed, misses, other = rewrite_content(content)
        total_misses += misses
        total_other += other
        if changed == 0:
            continue
        total_changed += changed
        up = requests.put(f"{BASE}/_emdash/api/content/{collection}/{ident}", headers=H,
                          json={"data": {"content": new_content}, "_rev": rev}, timeout=120)
        if up.status_code not in (200, 201):
            print(f"PUT fail {collection}/{ident} ({changed} refs): {up.status_code} {up.text[:150]}")
            continue
        urev = up.json()["data"]["_rev"]
        pub = requests.post(f"{BASE}/_emdash/api/content/{collection}/{ident}/publish", headers=H,
                            json={"_rev": urev}, timeout=120)
        if pub.status_code not in (200, 201):
            print(f"PUBLISH fail {collection}/{ident}: {pub.status_code} {pub.text[:150]}")
            continue
        updated.append(ident)
        print(f"  rewrote {collection}/{ident}: {changed} refs")
    print(f"TOTAL refs rewritten: {total_changed}, misses: {total_misses}, non-uploads untouched: {total_other}")
    print(f"items updated & republished: {len(updated)}")


if __name__ == "__main__":
    main()