# WordPress → EmDash Mapping

Decision log for migrating the WordPress `99Ways` site into the EmDash CMS on Astro.

## Collections

| WordPress | EmDash collection | Notes |
|---|---|---|
| `posts` (73) | `posts` | published, slugs preserved |
| `pages` (14) | `pages` | slugs preserved (incl. `home`) |
| — (new) | `categories` taxonomy | applied to both collections |

WordPress **tags** were omitted (the source has zero tags).

## Taxonomy

- WordPress `categories` → EmDash `categories` taxonomy (flat, not hierarchical).
- Only the 5 in-use categories were migrated; `Uncategorized` (0 posts) was dropped.
- Post slugs, titles, and permalinks are preserved 1:1.

## Authors / bylines

- 3 WordPress users → 3 EmDash **bylines** (guest credits, no CMS users created):
  Iman Nazari, Amin Heshmati, Moein Heshmati.
- Each post/page is credited to its original author via the primary byline.
- WordPress authors are not created as CMS logins (no password/email migration intended).

## Content conversion (Kadence Blocks → Portable Text)

Implemented in `migration/migrate.py` using BeautifulSoup on each item's rendered HTML:

| WordPress/Kadence element | EmDash Portable Text |
|---|---|
| `h1`–`h6` | heading blocks |
| `p`, `ul`, `ol`, `blockquote` | `normal`, `list` (bullet/number), `blockquote` |
| `pre` / code | `code` block |
| `a` (internal + external) | link mark (rewritten to local routes — see Links) |
| `img` | inline image block, **locally hosted** via the media map (see Images) |
| `strong` / `em` / inline `code` | `strong` / `em` / `code` marks |
| Kadence column / layout wrappers | flattened to inner content flow |
| Kadence info block / FAQ accordion | collapsed to visible inner text/images |
| Kadence table | rendered as a `code` block with pipe-delimited rows |
| Buttons | dropped (call-to-action buttons lose interaction value) |
| Kadence forms / dynamic blocks | dropped unless inner content present |
| Bare text before/after first tag in `<body>` | preserved as paragraph blocks |
| Inline text in container divs (e.g. paywall) | preserved as paragraph blocks (link marks retained) |

Other decisions:

- Slug field kept identical to WordPress for stable URLs where possible.
- Excerpts: WordPress excerpts preserved when present.
- Featured images: **all** locally hosted via the media library — no hotlinks remain.

## Images

### Full media migration (`migration/migrate-media.py`)

All 455 WordPress media files were uploaded to EmDash storage in-memory (downloaded from
the WP clone → streamed into `POST /media?deduplicate=true`): 453 migrated, 2 skipped
(SVG files, blocked by the EmDash global upload allowlist — `gemini-svg.svg` and
`Growth-Lever-Analytics-99Ways.svg`). The SVG file `gemini-svg.svg` also appears inline
in `academy`; that one reference is intentionally kept as a hotlink to the WP clone.

Featured images were reconciled: 74 duplicate uploads were deleted and the media-map was
patched to point featured-image fields at the correct existing media item, avoiding
`uploads/` bloat.

### Inline image rewrite (`migration/fix-content-media.py`)

All inline `img` URLs in Portable Text bodies were rewritten to local media URLs
(`/_emdash/api/media/file/<storageKey>`). The resolver matches by: exact original URL
→ unique basename → unique basename-without-extension → `-scaled` WordPress variant.
Two documented misses remain:

- `2025/05/1-1024x329.jpg` — 404 on the WordPress clone at migration time and
  ambiguous basename (3 different media share basename `1`), left as hotlink.
- `2026/08/gemini-svg.svg` — SVG, blocked by the upload allowlist.

### SEO image (`migration/apply-seo-image.py`)

`seo.image` set to the local media URL for 74 items (73 posts + 3 featured pages; 2 posts
whose featured media are SVGs and 11 pages without featured images are skipped).

## Internal links

`migration/fix-content-links.py` rewrote 394 internal WordPress-host references across
62 items to local routes:

| WordPress URL pattern | EmDash route |
|---|---|
| `https://99ways.instawp.dev/<slug>/` | `/posts/<slug>` or `/pages/<slug>` |
| `https://99ways.instawp.dev/category/<term>/` | `/category/<term>` |
| `https://99ways.instawp.dev/` | `/` |

Three internal targets could not be resolved (the slugs do not exist in the migrated
WP snapshots) and are left as hotlinks:

- `posthog-implementation-services` (referenced by `event-tracking-plan`)
- `a-b-testing-setup-in-shopify-with-posthog` (referenced by `how-to-set-up-a-posthog-alert-for-your-website`)
- `posthog-a-b-testing-on-wordpress` (referenced by the same post)

The `experiment-test-page` self-links with A/B test query parameters are left pointing at
the WP clone (they are test trigger URLs, not standard navigation).

## Dates

- Original WordPress `date_gmt` preserved as each item's `publishedAt` (backdated after
  seeding via `migration/backdate.py`). Posts 2024-09-09 → 2026-09-09.

## SEO

- Yoast `yoast_head_json.title` / `.description` applied as item `seo` title/description on
  all 73 posts + 14 pages (`migration/apply-seo.py`). Pages collection had `hasSeo` enabled
  to support this.
- `seo.image` set for all items with locally-hosted featured media (see Images).
- `canonical`, `og:*`, `robots` from Yoast were **not** migrated (source domain differs;
  canonical defaults are acceptable for the staging URL).

## Navigation

- WordPress `wp_navigation` → EmDash `primary` menu with 8 top-level items (label + URL),
  mirrored from the original header navigation.

## Site settings

- `title` = "99Ways", `tagline` = "Conversion rate optimization, experimentation & analytics".
- `favicon` = 99Ways favicon (1920-style mark, uploaded as media), `logo` left unset —
  branding is rendered inline by `src/components/Logo.astro`.
- Full WP site settings (`/wp-json/wp/v2/settings`) could not be captured (returns HTTP
  401 without credentials). The title/tagline/favicon were reconstructed from the rendered
  home page and set manually in EmDash. Other WP settings (timezone, posts-per-page,
  date format, etc.) were not transferable.

## Seed / content fidelity notes

- `seed/seed.json` is produced by `migrate.py` and is the canonical artifact for
  bootstrapping a fresh EmDash install of this site. It does not include media upload
  directives for inline images — the same post-processing scripts that fixed the live
  instance must be re-run after seeding (or seed regeneration should embed local
  media URLs once the media library is available at seed time).
- A data-loss bug in the original HTML→PT converter was discovered during fidelity
  verification: orphan direct text at body level and text interleaved with inline
  children inside block-level containers were dropped (gated teaser posts and Kadence
  dynamic pages were worst affected). The converter was fixed and `repair-content.py`
  reconverted all affected live items with image and link rewrites re-applied.

## Known limitations / non-goals

- SVG media is blocked by the EmDash global upload allowlist; five SVGs exist in the
  source; two were inline images, three are referenced as links/featured — only one
  (`gemini-svg.svg` in `academy`) remains as a hotlink.
- WordPress media has no usable `description` field in EmDash; only `alt` and `caption`
  were populated.
- Comments, forms, WooCommerce behaviour, Kadence interactive widgets (spacers,
  accordions in some contexts), and gating overlays are not recreated in EmDash.
- Three internal link targets (dead slugs) are left pointing at the WP clone (see Links).
- Full WordPress site settings could not be captured (401 without credentials).
- The WP clone domain remains hardcoded in the remaining intentional hotlinks
  listed above.