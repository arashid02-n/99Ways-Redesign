#!/usr/bin/env python3
"""
99Ways migration: set SEO OG image on every post/page that has a WordPress
featured image, using the local EmDash media URL from the media map.

Emdash supports Yoast top-level "title" and "description" (already applied by
migration/apply-seo.py) plus an OG image via seo.image. Yoast's canonical,
opengraph/schema payloads and robots rules have no 1:1 Emdash fields; see
migration/mapping.md for those decisions (canonical is intentionally left to
site defaults, OG is generated from seo.image).

Usage:
  EMDASH_TOKEN=ec_pat_* python3 migration/apply-seo-image.py
"""
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "wordpress-source")

TOKEN = os.environ["EMDASH_TOKEN"]
BASE = os.environ.get("EMDASH_URL", "http://localhost:4321")
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "X-EmDash-Request": "1",
    "Content-Type": "application/json",
}


def api(method, path, body=None):
    req = urllib.request.Request(f"{BASE}{path}", method=method, headers=HEADERS)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
    with urllib.request.urlopen(req, data=data, timeout=60) as r:
        return json.loads(r.read())


def main():
    media_map = json.load(open(os.path.join(SRC, "media-map.json")))
    updated = 0
    skipped = 0
    failed = 0
    for name, coll in (("posts", "posts"), ("pages", "pages")):
        for item in json.load(open(os.path.join(SRC, f"{name}.json"))):
            wfid = item.get("featured_media")
            ent = media_map.get(str(wfid or ""))
            if not ent or ent.get("status") != "migrated" or not ent.get("url"):
                skipped += 1
                continue
            try:
                api("PUT", f"/_emdash/api/content/{coll}/{item['slug']}", {"seo": {"image": ent["url"]}})
                updated += 1
            except urllib.error.HTTPError as e:
                failed += 1
                print(f"FAILED {coll}/{item['slug']}: HTTP {e.code}", file=sys.stderr)
    print(f"SEO image apply complete: {updated} updated, {skipped} skipped, {failed} failed.")


if __name__ == "__main__":
    main()