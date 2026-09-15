#!/usr/bin/env python3
"""
99Ways migration: WordPress (REST JSON) -> Emdash seed.json.

Reads the read-only WordPress snapshots in migration/wordpress-source/ and
produces:
  - seed/seed.json            schema + migrated content (Portable Text)
  - migration/migration-summary.json  counts + decisions
  - migration/dates.json      original publish dates (for optional backdating)

WordPress is treated strictly as read-only input.
"""
import json
import os
import re
from bs4 import BeautifulSoup, NavigableString, Tag

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "wordpress-source")
OUT_SEED = os.path.join(ROOT, "seed", "seed.json")

# --- Key generator -----------------------------------------------------------

class KeyGen:
    def __init__(self):
        self.n = 0

    def __call__(self):
        k = f"k{self.n:x}"
        self.n += 1
        return k

# --- Block-level helpers -----------------------------------------------------

BLOCK_HEADINGS = {"h1": "h1", "h2": "h2", "h3": "h3", "h4": "h4", "h5": "h5", "h6": "h6"}

# Kadence/WordPress layout containers whose children should be flattened.
LAYOUT_CONTAINERS = {
    "kb-row-layout-wrap",
    "kb-row-layout-id",
    "kadence-column",
    "kt-row-column-wrap",
    "kt-row-layout-inner",
    "kadence-rowlayout",
    "kadence-column",
    "wp-block-columns",
    "wp-block-column",
    "wp-block-group",
    "kadence-accordion",
    "kt-accordion",
    "wp-block-media-text",
}

# Elements to drop entirely (decorative / not representable).
DROPPED_CLASSES = {
    "kadence-spacer",
    "kadence-icon",
    "kadence-single-icon",
    "kadence-googlemaps",
    "kadence-posts",
    "kadence-postgrid",
    "kadence-query",
    "kadence-query-card",
    "kadence-advanced-form",
    "kadence-form",
    "wp-block-query",
    "wp-block-query-title",
    "wp-block-post-template",
    "wp-block-embed",
    "wp-block-embed-youtube",
    "wpforms",
    "wp-block-shortcode",
    "kt-blocks-info-box",
}

def class_list(tag):
    return set(tag.get("class", []))


def has_any_class(tag, names):
    return bool(class_list(tag) & set(names))


def is_layout_container(tag):
    classes = class_list(tag)
    # wp-block-columns / column are Gutenberg containers
    if classes & {"wp-block-columns", "wp-block-column", "wp-block-group"}:
        return True
    return bool(classes & {c for c in classes if c in LAYOUT_CONTAINERS or "rowlayout" in c or "kadence-column" in c})


def should_drop(tag):
    classes = class_list(tag)
    if classes & DROPPED_CLASSES:
        return True
    # any class containing known drop markers
    for c in classes:
        if any(m in c for m in ("spacer", "googlemap", "lottie", "advanced-form", "form-", "wpforms")):
            return True
    return False


def tag_name(tag):
    return tag.name.lower() if tag.name else ""


INLINE_TAGS = {
    "a", "span", "strong", "b", "em", "i", "br", "code", "kbd", "samp",
    "u", "small", "sub", "sup", "mark", "abbr", "s", "del", "strike", "img",
    "button", "time", "q", "cite", "label",
}


def is_inline(tag):
    return tag_name(tag) in INLINE_TAGS or hasattr(tag, "name") and not tag.name


# --- Inline parser -----------------------------------------------------------

def parse_inline(el, kg, mark_defs):
    """Return a list of PT spans for the inline content of `el`."""
    spans = []

    def push(text, marks=None):
        text = text.replace("\u00a0", " ")
        if text:
            spans.append({"_type": "span", "_key": kg(), "text": text, "marks": marks or []})

    def walk(node, marks):
        for child in node.children:
            if isinstance(child, NavigableString):
                push(str(child), marks)
            elif isinstance(child, Tag):
                name = tag_name(child)
                if name == "br":
                    push("\n", marks)
                elif name in ("strong", "b"):
                    walk(child, marks + ["strong"])
                elif name in ("em", "i"):
                    walk(child, marks + ["em"])
                elif name in ("del", "s", "strike"):
                    walk(child, marks + ["strike-through"])
                elif name in ("code", "kbd", "samp"):
                    walk(child, marks + ["code"])
                elif name == "a":
                    href = child.get("href")
                    if href:
                        mkey = kg()
                        mark_defs.append({"_type": "link", "_key": mkey, "href": href})
                        walk(child, marks + [mkey])
                    else:
                        walk(child, marks)
                elif name in ("sub", "sup", "u", "span", "small", "mark", "abbr"):
                    walk(child, marks)
                else:
                    # unexpected inline block: flatten its text
                    walk(child, marks)
            # ignore comments etc.

    walk(el, [])
    return spans


# --- Block walker ------------------------------------------------------------

def html_to_blocks(html_str):
    soup = BeautifulSoup(html_str or "", "html.parser")
    for s in soup(["script", "style", "noscript", "iframe", "svg", "head"]):
        s.decompose()

    blocks = []
    kg = KeyGen()

    def heading_block(tag):
        style = BLOCK_HEADINGS[tag_name(tag)]
        mark_defs = []
        spans = parse_inline(tag, kg, mark_defs)
        text = "".join(s.get("text", "") for s in spans).strip()
        if not text:
            return None
        return {"_type": "block", "_key": kg(), "style": style, "markDefs": mark_defs, "children": spans}

    def paragraph_block(tag):
        mark_defs = []
        spans = parse_inline(tag, kg, mark_defs)
        text = "".join(s.get("text", "") for s in spans).strip()
        if not text:
            return None
        return {"_type": "block", "_key": kg(), "style": "normal", "markDefs": mark_defs, "children": spans}

    def image_block(img_tag, alt=None):
        src = img_tag.get("src")
        if not src:
            return None
        # prefer the largest available: use data-full-url / data-large-file / src
        for attr in ("data-full-url", "data-large-file", "data-original", "src"):
            if img_tag.get(attr):
                src = img_tag[attr]
                break
        a = alt or img_tag.get("alt") or ""
        block = {"_type": "image", "_key": kg(), "alt": a, "asset": {"url": src}}
        w = img_tag.get("width")
        h = img_tag.get("height")
        if w:
            block["width"] = int(w) if str(w).isdigit() else None
        if h:
            block["height"] = int(h) if str(h).isdigit() else None
        if block.get("width") is None:
            block.pop("width", None)
        if block.get("height") is None:
            block.pop("height", None)
        return block

    def list_block(list_tag, level):
        ordered = tag_name(list_tag) == "ol"
        item_type = "number" if ordered else "bullet"
        out = []
        for li in list_tag.find_all("li", recursive=False):
            # inline content of the li (excluding nested lists)
            mark_defs = []
            # clone li without nested ul/ol
            clone = BeautifulSoup(str(li), "html.parser")
            for nested in clone(["ul", "ol"]):
                nested.decompose()
            spans = parse_inline(clone, kg, mark_defs)
            text = "".join(s.get("text", "") for s in spans).strip()
            if text:
                out.append({
                    "_type": "block", "_key": kg(), "style": "normal",
                    "listItem": item_type, "level": level,
                    "markDefs": mark_defs, "children": spans,
                })
            # nested lists
            for nested in li.find_all(["ul", "ol"], recursive=False):
                out.extend(list_block(nested, level + 1))
        return out

    def code_block(pre_tag):
        code = pre_tag.find("code") or pre_tag
        text = code.get_text()
        lang = None
        if code.name == "code":
            for c in code.get("class", []):
                if c.startswith("language-"):
                    lang = c[len("language-"):]
                    break
        return {"_type": "code", "_key": kg(), "language": lang, "code": text.rstrip("\n")}

    def table_block(table_tag):
        # Portable Text has no native table; flatten to monospace text lines.
        rows = []
        for tr in table_tag.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if cells:
                rows.append(" | ".join(cells))
        if not rows:
            return None
        return {"_type": "code", "_key": kg(), "language": None, "code": "\n".join(rows)}

    def gallery_block(figure_tag):
        out = []
        for img in figure_tag.find_all("img"):
            b = image_block(img)
            if b:
                out.append(b)
        return out

    def process(tag):
        name = tag_name(tag)

        if name in BLOCK_HEADINGS:
            b = heading_block(tag)
            if b:
                blocks.append(b)
            return

        if name == "pre":
            blocks.append(code_block(tag))
            return

        if name == "hr":
            blocks.append({"_type": "break", "_key": kg()})
            return

        if name == "table":
            b = table_block(tag)
            if b:
                blocks.append(b)
            return

        if name in ("ul", "ol"):
            blocks.extend(list_block(tag, 1))
            return

        if name == "blockquote":
            mark_defs = []
            spans = parse_inline(tag, kg, mark_defs)
            text = "".join(s.get("text", "") for s in spans).strip()
            if text:
                blocks.append({"_type": "block", "_key": kg(), "style": "blockquote", "markDefs": mark_defs, "children": spans})
            return

        if name == "figure":
            classes = class_list(tag)
            if "wp-block-image" in classes or tag.find("img"):
                imgs = tag.find_all("img")
                # gallery vs single image
                if "wp-block-gallery" in classes or "kadence-advancedgallery" in classes or len(imgs) > 1:
                    blocks.extend(gallery_block(tag))
                elif imgs:
                    b = image_block(imgs[0])
                    if b:
                        blocks.append(b)
                return
            if "wp-block-gallery" in classes or "kadence-advancedgallery" in classes:
                blocks.extend(gallery_block(tag))
                return
            # generic figure -> process children
            for child in tag.find_all(recursive=False):
                if isinstance(child, Tag):
                    process(child)
            return

        if name == "img":
            b = image_block(tag)
            if b:
                blocks.append(b)
            return

        classes = class_list(tag)

        # Kadence advanced heading -> heading (tag already h1-h6) or paragraph
        if "kadence-advancedheading" in classes or "kt-adv-heading" in " ".join(classes):
            if name in BLOCK_HEADINGS:
                b = heading_block(tag)
                if b:
                    blocks.append(b)
                    return
            b = paragraph_block(tag)
            if b:
                blocks.append(b)
            return

        # buttons -> paragraph with the link text
        if any(("btn" in c or "button" in c) for c in classes):
            links = tag.find_all("a")
            for a in links:
                txt = a.get_text(" ", strip=True)
                if txt:
                    mark_defs = []
                    mkey = kg()
                    href = a.get("href") or ""
                    if href:
                        mark_defs.append({"_type": "link", "_key": mkey, "href": href})
                    blocks.append({
                        "_type": "block", "_key": kg(), "style": "normal",
                        "markDefs": mark_defs,
                        "children": [{"_type": "span", "_key": kg(), "text": txt, "marks": [mkey] if href else []}],
                    })
            return

        # kadence image / single image wrappers
        if "kadence-image" in classes or "single-image" in classes:
            for img in tag.find_all("img"):
                b = image_block(img)
                if b:
                    blocks.append(b)
            return

        # drop decorative/dynamic/plugin blocks
        if should_drop(tag):
            return

        # layout containers -> flatten children
        if is_layout_container(tag):
            for child in tag.find_all(recursive=False):
                if isinstance(child, Tag):
                    process(child)
            return

        # paragraph-like leaf
        if name == "p":
            b = paragraph_block(tag)
            if b:
                blocks.append(b)
            return

        # default: recurse into children; if the tag has direct text, emit paragraph
        direct_text = "".join(str(c) for c in tag.children if isinstance(c, NavigableString)).strip()
        children_tags = [c for c in tag.find_all(recursive=False) if isinstance(c, Tag)]
        if direct_text and not children_tags:
            b = paragraph_block(tag)
            if b:
                blocks.append(b)
            return
        if direct_text and all(is_inline(c) for c in children_tags):
            # e.g. <div>Intro <a>link</a> and <b>bold</b>.</div>
            b = paragraph_block(tag)
            if b:
                blocks.append(b)
            return
        for child in children_tags:
            process(child)

    body = soup.body or soup
    for child in body.children:
        if isinstance(child, NavigableString):
            # orphan direct text at the top level (e.g. before the first tag)
            text = str(child).strip()
            if text:
                blocks.append({
                    "_type": "block", "_key": kg(), "style": "normal",
                    "markDefs": [],
                    "children": [{"_type": "span", "_key": kg(), "text": text, "marks": []}],
                })
        elif isinstance(child, Tag):
            process(child)

    # Filter out accidental empty blocks
    cleaned = []
    for b in blocks:
        if b.get("_type") == "block" and not b.get("children"):
            continue
        cleaned.append(b)
    return cleaned


# --- Utilities ---------------------------------------------------------------

def strip_html(html_str):
    if not html_str:
        return ""
    soup = BeautifulSoup(html_str, "html.parser")
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


def load(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return json.load(f)


def featured_media(post_or_page):
    media = (post_or_page.get("_embedded") or {}).get("wp:featuredmedia") or []
    if not media:
        return None
    m = media[0]
    src = m.get("source_url")
    if not src:
        return None
    filename = src.rsplit("/", 1)[-1].split("?")[0]
    return {
        "$media": {
            "url": src,
            "alt": m.get("alt_text") or "",
            "filename": filename,
        }
    }


def main():
    posts = load("posts.json")
    pages = load("pages.json")
    categories = load("categories.json")
    tags = load("tags.json")

    cat_by_id = {c["id"]: c for c in categories}

    # Sort content newest-first so insertion order preserves chronology.
    posts_sorted = sorted(posts, key=lambda p: p.get("date") or "", reverse=True)
    pages_sorted = sorted(pages, key=lambda p: p.get("date") or "", reverse=True)

    # --- Bylines -------------------------------------------------------------
    author_slugs = {}
    for p in posts:
        for a in p.get("authors", []):
            author_slugs[a["slug"]] = a.get("display_name") or a["slug"]
    bylines = []
    for slug in sorted(author_slugs):
        bylines.append({"id": f"byline:{slug}", "slug": slug, "displayName": author_slugs[slug]})
    byline_slug_to_id = {b["slug"]: b["id"] for b in bylines}

    # --- Taxonomy terms ------------------------------------------------------
    cat_terms = []
    for c in categories:
        if c["slug"] == "uncategorized" and c.get("count", 0) == 0:
            continue
        cat_terms.append({"id": f"term:category:{c['slug']}", "slug": c["slug"], "label": c["name"]})

    # --- Content -------------------------------------------------------------
    post_entries = []
    dates = []
    for p in posts_sorted:
        slug = p["slug"]
        cats = [cat_by_id[cid]["slug"] for cid in p.get("categories", []) if cid in cat_by_id]
        cats = [c for c in cats if c != "uncategorized"]
        data = {
            "title": p["title"]["rendered"],
            "excerpt": strip_html(p["excerpt"].get("rendered", "")),
            "content": html_to_blocks(p["content"].get("rendered", "")),
        }
        fm = featured_media(p)
        if fm:
            data["featured_image"] = fm
        entry = {
            "id": f"post:{slug}",
            "slug": slug,
            "status": "published",
            "data": data,
            "taxonomies": {"category": cats},
        }
        byline_ids = [byline_slug_to_id[a["slug"]] for a in p.get("authors", []) if a["slug"] in byline_slug_to_id]
        if byline_ids:
            entry["bylines"] = [{"byline": bid} for bid in byline_ids]
        post_entries.append(entry)
        if p.get("date"):
            dates.append({"collection": "posts", "slug": slug, "publishedAt": p["date"]})

    page_entries = []
    for p in pages_sorted:
        slug = p["slug"]
        data = {
            "title": p["title"]["rendered"],
            "content": html_to_blocks(p["content"].get("rendered", "")),
        }
        fm = featured_media(p)
        if fm:
            data["featured_image"] = fm
        entry = {
            "id": f"page:{slug}",
            "slug": slug,
            "status": "published",
            "data": data,
        }
        page_entries.append(entry)
        if p.get("date"):
            dates.append({"collection": "pages", "slug": slug, "publishedAt": p["date"]})

    # --- Seed document -------------------------------------------------------
    seed = {
        "$schema": "https://emdashcms.com/seed.schema.json",
        "version": "1",
        "meta": {
            "name": "99Ways",
            "description": "99Ways — conversion rate optimization, experimentation, and analytics. Migrated from WordPress.",
            "author": "99Ways",
        },
        "settings": {
            "title": "99Ways",
            "tagline": "Conversion rate optimization, experimentation & analytics",
        },
        "defaultLocale": "en",
        "collections": [
            {
                "slug": "pages",
                "label": "Pages",
                "labelSingular": "Page",
                "supports": ["drafts", "revisions", "search"],
                "fields": [
                    {"slug": "title", "label": "Title", "type": "string", "required": True, "searchable": True},
                    {"slug": "featured_image", "label": "Featured Image", "type": "image"},
                    {"slug": "content", "label": "Content", "type": "portableText", "searchable": True},
                ],
            },
            {
                "slug": "posts",
                "label": "Posts",
                "labelSingular": "Post",
                "supports": ["drafts", "revisions", "search", "seo"],
                "fields": [
                    {"slug": "title", "label": "Title", "type": "string", "required": True, "searchable": True},
                    {"slug": "featured_image", "label": "Featured Image", "type": "image"},
                    {"slug": "content", "label": "Content", "type": "portableText", "searchable": True},
                    {"slug": "excerpt", "label": "Excerpt", "type": "text"},
                ],
            },
        ],
        "taxonomies": [
            {
                "id": "tax:category",
                "name": "category",
                "label": "Categories",
                "labelSingular": "Category",
                "hierarchical": True,
                "collections": ["posts"],
                "terms": cat_terms,
            },
            {
                "id": "tax:tag",
                "name": "tag",
                "label": "Tags",
                "labelSingular": "Tag",
                "hierarchical": False,
                "collections": ["posts"],
                "terms": [],
            },
        ],
        "menus": [
            {
                "id": "menu:primary",
                "name": "primary",
                "label": "Primary Navigation",
                "items": [
                    {"type": "custom", "label": "Home", "url": "/"},
                    {"type": "custom", "label": "Blog", "url": "/posts"},
                    {"type": "custom", "label": "Hire CRO Expert", "url": "/pages/hire-cro-expert"},
                    {"type": "custom", "label": "Contact Form", "url": "/pages/contact-form"},
                    {"type": "custom", "label": "Schedule", "url": "/pages/book-your-free-consultation"},
                    {"type": "custom", "label": "Official References & Profiles", "url": "/pages/official-references-profiles"},
                    {"type": "custom", "label": "Privacy & Cookie Policy", "url": "/pages/privacy-policy"},
                    {"type": "custom", "label": "Terms of Use", "url": "/pages/terms-of-use"},
                ],
            }
        ],
        "widgetAreas": [
            {
                "name": "sidebar",
                "label": "Sidebar",
                "description": "Widgets shown alongside post articles",
                "widgets": [
                    {"type": "component", "title": "Recent Posts", "componentId": "core:recent-posts", "props": {}},
                    {"type": "component", "title": "Categories", "componentId": "core:categories", "props": {}},
                    {"type": "component", "title": "Tags", "componentId": "core:tags", "props": {}},
                ],
            }
        ],
        "bylines": bylines,
        "content": {
            "posts": post_entries,
            "pages": page_entries,
        },
    }

    os.makedirs(os.path.dirname(OUT_SEED), exist_ok=True)
    with open(OUT_SEED, "w", encoding="utf-8") as f:
        json.dump(seed, f, ensure_ascii=False, indent="\t")

    with open(os.path.join(HERE, "dates.json"), "w", encoding="utf-8") as f:
        json.dump(dates, f, ensure_ascii=False, indent=2)

    summary = {
        "posts": len(post_entries),
        "pages": len(page_entries),
        "categories": len(cat_terms),
        "tags": len(tags),
        "bylines": len(bylines),
        "featured_images_posts": sum(1 for e in post_entries if "featured_image" in e["data"]),
        "featured_images_pages": sum(1 for e in page_entries if "featured_image" in e["data"]),
    }
    with open(os.path.join(HERE, "migration-summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
