#!/usr/bin/env python3
"""Full-content fidelity verification of every migrated item against the
read-only WordPress snapshots.

For each post/page it checks slug, title, publishedAt (== WordPress
date_gmt), category term assignment, featured-image presence, and word-level
content similarity between the WordPress rendered HTML and the Emdash
Portable Text body. A similarity < 0.85 or any structural mismatch is
reported as a possible discrepancy for human review.

Usage:
  EMDASH_TOKEN=ec_pat_* python3 migration/verify-content.py
"""
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "wordpress-source")

TOKEN = os.environ["EMDASH_TOKEN"]
BASE = os.environ.get("EMDASH_URL", "http://localhost:4321")
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "X-EmDash-Request": "1",
}

THRESHOLD = 0.85
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def api(path):
    req = urllib.request.Request(f"{BASE}{path}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def wp_text(rendered):
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(rendered or "", "html.parser")
        # drop Kadence dynamic widgets (latest-posts loops, archive loops,
        # tag-cloud blocks) whose rendered text is generated live from other
        # content and duplicated across pages on the source site
        for sel in (
            ".kt-blocks-post-loop-block",
            ".kt-post-grid-wrap",
            ".wp-block-kadence-postgrid",
            ".wp-block-kadence-queryloop",
            ".wp-block-kadence-latestposts",
            ".wp-block-kadence-postgrid",
            ".kt-blocks-tagcloud",
        ):
            for el in soup.select(sel):
                el.decompose()
        rendered = str(soup)
    except Exception:
        pass
    text = re.sub(r"<style[^>]*>.*?</style>", " ", rendered or "", flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = html.unescape(TAG_RE.sub(" ", text))
    return set(WS_RE.sub(" ", text).strip().lower().split())


def em_text(content):
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
    return set(" ".join(words).lower().split())


def similarity(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / max(len(a), len(b))


def missing_prose(a, b):
    if not a:
        return set()
    return a - b


def main():
    cat_terms = {c["id"]: c["slug"] for c in json.load(open(os.path.join(SRC, "categories.json")))}
    report = {"posts": [], "pages": []}
    summary = {"matched": 0, "issues": 0, "total": 0}
    for name, coll in (("posts", "posts"), ("pages", "pages")):
        for item in json.load(open(os.path.join(SRC, f"{name}.json"))):
            summary["total"] += 1
            issues = []
            slug = item["slug"]
            try:
                it = api(f"/_emdash/api/content/{coll}/{urllib.parse.quote(slug)}")["data"]["item"]
            except urllib.error.HTTPError as e:
                issues.append(f"fetch failed HTTP {e.code}")
                summary["issues"] += 1
                report[name].append({"slug": slug, "ok": False, "issues": issues})
                continue
            data = it["data"]
            if data.get("title") != item["title"]["rendered"]:
                issues.append(f"title changed: {data.get('title')!r} != {item['title']['rendered']!r}")
            wp_date = (item.get("date_gmt") or "").replace("+00:00", "Z").replace(" ", "T")
            if not wp_date.endswith("Z"):
                wp_date += "Z"
            emdash_date = it.get("publishedAt")
            if (emdash_date or "")[:19] != wp_date[:19]:
                issues.append(f"publishedAt {emdash_date} != wp {wp_date}")
            wcats = {cat_terms[i] for i in item.get("categories", []) if i in cat_terms}
            terms = api(f"/_emdash/api/content/{coll}/{urllib.parse.quote(slug)}/terms/category")["data"]["terms"]
            ecats = {t["slug"] for t in terms}
            if wcats != ecats:
                issues.append(f"categories {sorted(ecats)} != wp {sorted(wcats)}")
            wfeat = bool(item.get("featured_media"))
            efeat = bool(data.get("featured_image"))
            if wfeat != efeat:
                issues.append(f"featured image mismatch wp={wfeat} em={efeat}")
            wp_words = wp_text(item["content"]["rendered"])
            em_words = em_text(data.get("content"))
            sim = similarity(wp_words, em_words)
            if sim < THRESHOLD:
                # low similarity is only a problem when real source prose is absent
                missing = missing_prose(wp_words, em_words)
                if missing:
                    extras = [w for w in sorted(missing) if len(w) > 3]
                    issues.append(f"content similarity {sim:.2f} < {THRESHOLD} (missing {len(missing)} words, e.g. {', '.join(extras[:6])})")
            entry = {"slug": slug, "ok": not issues, "similarity": round(sim, 3), "issues": issues}
            if issues:
                summary["issues"] += 1
            else:
                summary["matched"] += 1
            report[name].append(entry)
    json.dump(report, open(os.path.join(SRC, "content-verification.json"), "w"), ensure_ascii=False, indent=2)
    print(summary)
    for name in ("posts", "pages"):
        for e in report[name]:
            if e["ok"]:
                continue
            print(f"  [{name}] {e['slug']}: " + "; ".join(e["issues"]))


if __name__ == "__main__":
    main()