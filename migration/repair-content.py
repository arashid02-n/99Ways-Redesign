#!/usr/bin/env python3
"""Repair live Emdash content that lost text during the first migration pass.

migration/migrate.py's original HTML->PortableText walker dropped orphan
direct text: text before the first tag at body level, and text interleaved
with inline children inside otherwise block-level containers (gated "paywall"
teaser posts and Kadence-built pages). This script re-runs the *fixed*
converter on every item, and where the fresh conversion carries meaningfully
more text than the live content, replaces the live content with it and then
re-applies the local-media and internal-link rewrites (the same idempotent
transformations migration/fix-content-media.py and
migration/fix-content-links.py do).

Usage:
  EMDASH_TOKEN=ec_pat_* python3 migration/repair-content.py
"""
import json
import os
import sys
import urllib.parse

import requests

import importlib.util

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from migrate import html_to_blocks  # noqa: E402


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(os.path.abspath(__file__)), path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


media_mod = load_module("fix_content_media", "fix-content-media.py")
link_mod = load_module("fix_content_links", "fix-content-links.py")
resolve_image = media_mod.resolve
rewrite_href = link_mod.rewrite_href
load_slugs = link_mod.load_slugs

BASE = "http://localhost:4321"
TOKEN = os.environ.get("EMDASH_TOKEN")
if not TOKEN:
    sys.exit("EMDASH_TOKEN env var is required")
H = {"Authorization": f"Bearer {TOKEN}", "X-EmDash-Request": "1"}
SRC = "migration/wordpress-source"
GAIN = 1.08  # replace content when fresh conversion has >=8% more words


def count_text(content):
    words = []

    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("text"), str):
                words.extend(node["text"].split())
            elif isinstance(node.get("code"), str):
                words.extend(node["code"].split())
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(content)
    return len(words)


def rewrite_urls(content):
    def walk(node):
        if isinstance(node, dict):
            asset = node.get("asset")
            if isinstance(asset, dict) and isinstance(asset.get("url"), str):
                new = resolve_image(asset["url"])
                if new and new != "MISS":
                    asset["url"] = new
            if isinstance(node.get("href"), str):
                new = rewrite_href(node["href"], route, cat_slugs)
                if new:
                    node["href"] = new
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(content)
    return content


def main():
    global route, cat_slugs
    route, cat_slugs = load_slugs()
    wp = {}
    for name in ("posts", "pages"):
        for it in json.load(open(os.path.join(SRC, f"{name}.json"))):
            wp[it["slug"]] = it

    repaired = 0
    for dump, collection in (
        ("/tmp/99ways-tmp/posts_dump.json", "posts"),
        ("/tmp/99ways-tmp/pages_live.json", "pages"),
    ):
        for it in json.load(open(dump))["data"]["items"]:
            slug = it.get("slug")
            src = wp.get(slug)
            if not src:
                continue
            r = requests.get(f"{BASE}/_emdash/api/content/{collection}/{urllib.parse.quote(slug)}?draft=false", headers=H, timeout=60)
            if r.status_code != 200:
                continue
            body = r.json()["data"]
            rev = body["_rev"]
            live = body["item"]["data"].get("content")

            fresh = html_to_blocks(src["content"]["rendered"])
            if count_text(fresh) < count_text(live) * GAIN:
                continue
            fresh = rewrite_urls(fresh)
            up = requests.put(f"{BASE}/_emdash/api/content/{collection}/{urllib.parse.quote(slug)}", headers=H,
                              json={"data": {"content": fresh}, "_rev": rev}, timeout=120)
            if up.status_code not in (200, 201):
                print(f"PUT fail {collection}/{slug}: {up.status_code} {up.text[:120]}")
                continue
            urv = up.json()["data"]["_rev"]
            pub = requests.post(f"{BASE}/_emdash/api/content/{collection}/{urllib.parse.quote(slug)}/publish", headers=H,
                                json={"_rev": urv}, timeout=120)
            if pub.status_code not in (200, 201):
                print(f"PUBLISH fail {collection}/{slug}: {pub.status_code}")
                continue
            repaired += 1
            print(f"  repaired {collection}/{slug}")

    print(f"TOTAL repaired: {repaired}")


if __name__ == "__main__":
    main()