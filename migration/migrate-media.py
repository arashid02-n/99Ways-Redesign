#!/usr/bin/env python3
"""Migrate the full WordPress media library (455 items) into EmDash.

Reads migration/wordpress-source/media.json (read-only snapshot), downloads
each file in memory and uploads it to the running EmDash instance via the
REST multipart upload route (deduplicated by content hash so already-migrated
featured images map onto the same item). Then applies alt text and captions
via PUT /_emdash/api/media/:id.

EmDash has no media "description" field and blocks SVG uploads by global
MIME allowlist; both are recorded in the output map and documented in
migration/mapping.md.

Usage:
  EMDASH_TOKEN=ec_pat_* python3 migration/migrate-media.py

Output:
  migration/wordpress-source/media-map.json  # wp media id -> emdash mapping
  migration/wordpress-source/media-map-report.txt
"""
import json
import os
import sys
import time

import requests

BASE = "http://localhost:4321"
TOKEN = os.environ.get("EMDASH_TOKEN")
if not TOKEN:
    sys.exit("EMDASH_TOKEN env var is required")
H = {"Authorization": f"Bearer {TOKEN}", "X-EmDash-Request": "1"}
SRC = "migration/wordpress-source/media.json"
OUT = "migration/wordpress-source/media-map.json"
REPORT = "migration/wordpress-source/media-map-report.txt"
UA = {"User-Agent": "Mozilla/5.0 (99Ways migration read-only)"}

BLOCKED_MIME = ("image/svg+xml",)  # excluded from EmDash global upload allowlist


def upload_mem(filename, data, mime):
    files = {"file": (filename, data, mime)}
    form = {"deduplicate": "true"}
    r = requests.post(f"{BASE}/_emdash/api/media", headers=H, files=files, data=form, timeout=180)
    return r


def set_meta(media_id, alt, caption):
    body = {}
    if alt:
        body["alt"] = alt
    if caption:
        body["caption"] = caption
    if not body:
        return True
    r = requests.put(f"{BASE}/_emdash/api/media/{media_id}", headers=H, json=body, timeout=60)
    return r.status_code in (200, 201)


def main():
    media = json.load(open(SRC))
    if os.path.exists(OUT):
        mapping = json.load(open(OUT))
    else:
        mapping = {}

    skipped = []
    errors = []
    new_names = set()
    for i, m in enumerate(media, 1):
        wid = str(m["id"])
        if wid in mapping:
            continue
        mime = m.get("mime_type", "")
        src = m.get("source_url", "")
        if not src:
            errors.append((wid, m.get("slug", ""), "no source_url"))
            continue
        if any(mime.startswith(b) for b in BLOCKED_MIME):
            skipped.append({"id": wid, "slug": m.get("slug"), "mime": mime, "source_url": src})
            mapping[wid] = {"status": "skipped", "mime": mime, "source_url": src}
            continue
        try:
            dl = requests.get(src, timeout=120, headers=UA)
            if dl.status_code != 200:
                errors.append((wid, m.get("slug", ""), f"download {dl.status_code}"))
                continue
        except Exception as e:  # noqa: BLE001
            errors.append((wid, m.get("slug", ""), f"download error {e}"))
            continue
        ext = src.rsplit(".", 1)[-1] if "." in src else ""
        fname = f"{m.get('slug', wid)}.{ext}"
        try:
            resp = upload_mem(fname, dl.content, mime)
        except Exception as e:  # noqa: BLE001
            errors.append((wid, m.get("slug", ""), f"upload error {e}"))
            continue
        if resp.status_code not in (200, 201):
            errors.append((wid, m.get("slug", ""), f"upload {resp.status_code} {resp.text[:120]}"))
            continue
        item = resp.json()["data"]["item"]
        eid = item["id"]
        stkey = item["storageKey"]
        folder = "/".join(src.split("/wp-content/uploads/")[-1].split("/")[:-1])
        fbase = src.split("/")[-1]
        stem = fbase.rsplit(".", 1)[0] if "." in fbase else fbase
        base_src = src
        if "-" in stem and stem.rsplit("-", 1)[-1] and stem.rsplit("-", 1)[-1].isdigit():
            pass  # source_url is normally the base file; keep as-is
        alt = (m.get("alt_text") or "").strip() or None
        caption = ((m.get("caption") or {}).get("rendered") or "").strip() or None
        ok = set_meta(eid, alt, caption)
        mapping[wid] = {
            "status": "migrated",
            "id": eid,
            "storageKey": stkey,
            "url": f"/_emdash/api/media/file/{stkey}",
            "filename": fbase,
            "folder": folder,
            "basename": stem,
            "mime": mime,
            "alt": alt,
            "caption": caption,
            "meta_set": ok,
        }
        new_names.add(stkey.rsplit(".", 1)[0].split("_")[0])
        if i % 25 == 0:
            json.dump(mapping, open(OUT, "w"), ensure_ascii=False, indent=2)
            print(f"  ... {i}/{len(media)} processed ({len(errors)} errors)")
    json.dump(mapping, open(OUT, "w"), ensure_ascii=False, indent=2)

    report = {
        "total_wp_media": len(media),
        "migrated": sum(1 for v in mapping.values() if v.get("status") == "migrated"),
        "skipped_svg": len(skipped),
        "errors": errors,
        "skipped": skipped,
    }
    json.dump(report, open(REPORT, "w"), ensure_ascii=False, indent=2)
    print(json.dumps({k: report[k] for k in ("total_wp_media", "migrated", "skipped_svg")}))
    print(f"errors: {len(errors)}")
    for e in errors[:10]:
        print("   ", e)


if __name__ == "__main__":
    main()