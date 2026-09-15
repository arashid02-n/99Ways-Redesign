#!/usr/bin/env python3
"""Rewrite internal WordPress links in live posts/pages to local Emdash routes.

The read-only WordPress host (99ways.instawp.dev) will not survive the
migration, so internal hyperlinks pointing at it are mapped onto the
corresponding migrated Emdash routes:

  https://99ways.instawp.dev/<post-slug>/   -> /posts/<post-slug>
  https://99ways.instawp.dev/<page-slug>/   -> /pages/<page-slug>
  https://99ways.instawp.dev/category/<t>/  -> /category/<t>
  https://99ways.instawp.dev/               -> /

Targets that do not match a migrated item (deleted posts, editor draft links,
external hosts) are left untouched and counted in the report. Query strings
and fragments are preserved.

Usage:
  EMDASH_TOKEN=ec_pat_* python3 migration/fix-content-links.py
"""
import json
import os
import re
import sys
import urllib.parse

import requests

BASE = "http://localhost:4321"
TOKEN = os.environ.get("EMDASH_TOKEN")
if not TOKEN:
    sys.exit("EMDASH_TOKEN env var is required")
H = {"Authorization": f"Bearer {TOKEN}", "X-EmDash-Request": "1"}
SRC = "migration/wordpress-source"

WP_HOST = "99ways.instawp.dev"


def load_slugs():
    route = {}
    for name, prefix in (("posts", "posts"), ("pages", "pages")):
        for it in json.load(open(os.path.join(SRC, f"{name}.json"))):
            route[it["slug"]] = f"/{prefix}/{it['slug']}"
    cats = json.load(open(os.path.join(SRC, "categories.json")))
    cat_slugs = {c["slug"] for c in cats}
    return route, cat_slugs


def rewrite_href(href, route, cat_slugs):
    try:
        parts = urllib.parse.urlsplit(href)
    except ValueError:
        return None
    if parts.netloc != WP_HOST:
        return None
    path = parts.path.rstrip("/")
    if path == "":
        return "/" + (f"?{parts.query}" if parts.query else "") + (f"#{parts.fragment}" if parts.fragment else "")
    segs = [s for s in path.split("/") if s]
    if len(segs) >= 2 and segs[0] == "category" and segs[1] in cat_slugs:
        new = f"/category/{segs[1]}"
    elif len(segs) == 1 and segs[0] in route:
        new = route[segs[0]]
    else:
        return None  # unresolved internal target
    suffix = (f"?{parts.query}" if parts.query else "") + (f"#{parts.fragment}" if parts.fragment else "")
    return new + suffix


def main():
    route, cat_slugs = load_slugs()
    changed_items = 0
    total = 0
    unresolved = {}
    for dump, collection in (
        ("/tmp/99ways-tmp/posts_dump.json", "posts"),
        ("/tmp/99ways-tmp/pages_live.json", "pages"),
    ):
        slugs = [it["slug"] for it in json.load(open(dump))["data"]["items"] if it.get("slug")]
        for ident in sorted(slugs):
            r = requests.get(f"{BASE}/_emdash/api/content/{collection}/{ident}?draft=false", headers=H, timeout=60)
            if r.status_code != 200:
                continue
            body = r.json()["data"]
            rev = body["_rev"]
            content = body["item"]["data"].get("content")

            n_rewritten = [0]

            def walk(node):
                if isinstance(node, dict):
                    if isinstance(node.get("href"), str):
                        new = rewrite_href(node["href"], route, cat_slugs)
                        if new:
                            if node["href"] != new:
                                node["href"] = new
                                n_rewritten[0] += 1
                        elif node["href"].startswith(f"https://{WP_HOST}"):
                            unresolved[collection + "/" + ident] = unresolved.get(collection + "/" + ident, 0) + 1
                    for v in node.values():
                        walk(v)
                elif isinstance(node, list):
                    for v in node:
                        walk(v)

            walk(content)
            if n_rewritten[0] == 0:
                continue
            up = requests.put(f"{BASE}/_emdash/api/content/{collection}/{ident}", headers=H,
                              json={"data": {"content": content}, "_rev": rev}, timeout=120)
            if up.status_code not in (200, 201):
                print(f"PUT fail {collection}/{ident}: {up.status_code}")
                continue
            urv = up.json()["data"]["_rev"]
            pub = requests.post(f"{BASE}/_emdash/api/content/{collection}/{ident}/publish", headers=H,
                                json={"_rev": urv}, timeout=120)
            if pub.status_code not in (200, 201):
                print(f"PUBLISH fail {collection}/{ident}: {pub.status_code}")
                continue
            changed_items += 1
            total += n_rewritten[0]
            print(f"  links {collection}/{ident}: {n_rewritten[0]}")
    print(f"TOTAL internal links rewritten: {total} across {changed_items} items")
    print(f"unresolved internal target counts: {sum(unresolved.values())}")
    for k, v in sorted(unresolved.items()):
        print(f"   {k}: {v}")


if __name__ == "__main__":
    main()