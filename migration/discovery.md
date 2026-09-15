# WordPress Source Discovery

Documentation of the WordPress source site `99Ways` (clone at `https://99ways.instawp.dev`),
captured on 2026-09-15 for the migration to EmDash. The source is treated as **read-only**;
raw responses are preserved verbatim under `migration/wordpress-source/`.

## Site overview

| Property | Value |
|---|---|
| Site name | 99Ways |
| Platform | WordPress (InstaWP clone) |
| Home URL | `https://99ways.instawp.dev` |
| Rendered HTML plugin | Kadence theme + Kadence Blocks (heavy use) |
| SEO plugin | Yoast SEO 28.4 (`yoast_head` / `yoast_head_json` present on all items) |
| Cart/auth | WooCommerce styled pages exist (register/login/my-account) — no store migrated |

## Content counts

| Type | Count | Notes |
|---|---|---|
| Posts | 73 | All published, all have featured media, 2024-09-09 → 2026-09-09 |
| Pages | 14 | Includes home + WooCommerce-style pages |
| Media | 455 | All images; 453 migrated, 2 SVG skipped (see mapping.md) |
| Categories | 5 used | + `Uncategorized` (0 posts, skipped) |
| Tags | 0 | — |
| Authors | 3 | Iman Nazari, Amin Heshmati, Moein Heshmati |
| Navigation | 1 | `wp_navigation` "Navigation" (published) |

Posts by category:

- Guides and How-tos — 37
- Optimization Experiences — 18
- PostHog Feature Breakdowns — 15
- Tools Comparison — 4
- Featured Experiments — 4

Posts by author: author 4 → 30, author 2 → 22, author 1 → 21.

## Content characteristics

- Post body rendering totals ~1.79M characters of HTML across 73 posts.
- Content is authored in **Kadence Blocks**: column layouts, info blocks, FAQ accordions,
  tables, buttons, and hero sections. The converter (`migration/migrate.py`) flattens these
  into Portable Text preserving headings, paragraphs, lists, blockquotes, code blocks,
  links, and inline images; complex Kadence-specific widgets are reduced to their inner
  text/images (see `mapping.md`).
- Roughly a fifth of the posts are **gated teasers**: a paywall notice ("Subscribe or log
  in to read the rest of this content") produced by the leaking-paywall plugin. The
  converter preserves the notice and its links.
- `content.rendered` embeds large Kadence `<style>` blocks on block-built pages; these are
  removed by the converter and excluded from fidelity comparisons.
- Several pages are built entirely from **dynamic Kadence widgets** (e.g. `academy` is a
  latest-posts grid rendering recent blog posts inline, `experiment-test-page` self-links
  with A/B test query parameters). Dynamic widget text is dropped from migration and from
  fidelity comparison; the static text that remains on those pages is migrated.
- Kadence `buttons`, forms (Kadence Forms / advanced forms), gating, and other interactive
  widgets are dropped or reduced (see `mapping.md`). WordPress media has no usable
  "description" in EmDash (media supports `alt` + `caption` only).

## API endpoints captured

Each response saved raw from the source API (best-effort, key-ed access):

- `posts.json` (4.4 MB, 73 posts), `pages.json` (697 KB, 14 pages)
- `media.json` (1.3 MB, 455 media), `categories.json`, `tags.json`
- `types.json` (includes custom post types: `kadence_*`, `sp_*` accordion/popup,
  `wp_*` blocks, `elementor_*`, etc. — none contain content to migrate)
- `taxonomies.json`, `navigation.json`, `api-root.json`

## Data not capturable

- `wp/v2/settings` returns **HTTP 401** (requires Wordfeeds-style authentication; no WP
  credentials available). The source `settings.json` therefore cannot be captured and is
  absent from the snapshot. Site title/tagline were instead read from the rendered home
  page and set in EmDash site settings (mapping.md). Option was documented, not fabricated.
- No me-capable `/wp/v2/users` session; authors were reconstructed from the author
  fields present in the post/page objects (author id + name + link).

## Files

- `migration/wordpress-source/*.json` — raw API snapshots (read-only reference)
- `migration/wordpress-source/media-map.json` / `media-map-report.txt` — WP media id ↔
  EmDash media id map produced by `migrate-media.py`
- `migration/wordpress-source/content-verification.json` — full fidelity report produced
  by `verify-content.py` (87/87 items clean)
- `migration/migrate.py` — HTML → Portable Text converter + seed generator
- `migration/backdate.py` — restore original `date_gmt` as publish dates
- `migration/apply-seo.py` — apply Yoast `title`/`description` as item SEO
- `migration/migrate-media.py` — bulk media upload (WP → EmDash, dedup)
- `migration/media-reconcile-featured.py` — de-duplicate featured media re-uploads
- `migration/fix-content-media.py` — rewrite inline images to local media URLs
- `migration/fix-content-links.py` — rewrite internal WP links to local routes
- `migration/apply-seo-image.py` — set `seo.image` from the media map
- `migration/verify-content.py` — full fidelity verification (87/87 clean)
- `migration/repair-content.py` — re-convert gated/teaser items that lost text in the
  first pass, then re-apply media + link rewrites
- `seed/seed.json` — generated EmDash seed (schema + all content, ~4.8 MB)