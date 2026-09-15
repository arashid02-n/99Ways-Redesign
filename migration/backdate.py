#!/usr/bin/env python3
"""
99Ways migration: backdate Emdash publish dates to the original WordPress dates.

Reads the read-only WordPress snapshots (migration/wordpress-source/) and
re-publishes each migrated post/page with its original `date_gmt` via the
Emdash content publish endpoint (which accepts `publishedAt` to backdate).

Usage:
  EMDASH_TOKEN=ec_pat_... EMDASH_URL=http://localhost:4321 python3 migration/backdate.py
"""
import json
import os
import sys
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


def original_dates():
    """Map (collection, slug) -> date_gmt in ISO-8601 UTC."""
    out = {}
    for name, coll in (("posts", "posts"), ("pages", "pages")):
        for item in json.load(open(os.path.join(SRC, f"{name}.json"))):
            dg = item.get("date_gmt")
            if dg:
                out[(coll, item["slug"])] = dg + "Z" if not dg.endswith("Z") else dg
    return out


def list_collection(coll):
    items = []
    cursor = None
    while True:
        url = f"/_emdash/api/content/{coll}?limit=100"
        if cursor:
            url += f"&cursor={cursor}"
        d = api("GET", url)
        data = d["data"]
        items.extend(data["items"])
        cursor = data.get("nextCursor")
        if not cursor:
            break
    return items


def main():
    dates = original_dates()
    updated = 0
    skipped = 0
    for coll in ("posts", "pages"):
        items = list_collection(coll)
        for it in items:
            slug = it["slug"]
            key = (coll, slug)
            if key not in dates:
                skipped += 1
                continue
            publishedAt = dates[key]
            try:
                api("POST", f"/_emdash/api/content/{coll}/{slug}/publish", {"publishedAt": publishedAt})
                updated += 1
                print(f"backdated {coll}/{slug} -> {publishedAt}")
            except Exception as e:
                print(f"FAILED {coll}/{slug}: {e}", file=sys.stderr)
    print(f"\nBackdating complete: {updated} updated, {skipped} skipped (no original date).")


if __name__ == "__main__":
    main()
