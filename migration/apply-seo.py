#!/usr/bin/env python3
"""
99Ways migration: apply Yoast SEO metadata (title, description) from the
read-only WordPress snapshots to Emdash items via the content update API.

Usage:
  python3 migration/apply-seo.py
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
    updated = 0
    skipped = 0
    failed = 0
    for name, coll in (("posts", "posts"), ("pages", "pages")):
        for item in json.load(open(os.path.join(SRC, f"{name}.json"))):
            j = item.get("yoast_head_json") or {}
            title = (j.get("title") or "").strip()
            desc = (j.get("description") or "").strip()
            if not title and not desc:
                skipped += 1
                continue
            seo = {}
            if title:
                seo["title"] = title
            if desc:
                seo["description"] = desc
            if not seo:
                skipped += 1
                continue
            try:
                api("PUT", f"/_emdash/api/content/{coll}/{item['slug']}", {"seo": seo})
                updated += 1
            except urllib.error.HTTPError as e:
                failed += 1
                print(f"FAILED {coll}/{item['slug']}: HTTP {e.code}", file=sys.stderr)
    print(f"SEO apply complete: {updated} updated, {skipped} skipped, {failed} failed.")


if __name__ == "__main__":
    main()