# Migration Verification

How the WordPress → EmDash migration was verified. All checks ran against the live EmDash
site at `http://localhost:4321` (dev mode) via the EmDash REST interface and curl.

## Counts (source vs migrated)

| Item | WordPress | EmDash (verified) |
|---|---|---|
| Posts | 73 | 73 |
| Pages | 14 | 14 |
| Categories | 5 used | 5 |
| Bylines | 3 authors | 3 |
| Tags | 0 | 0 |
| Nav menu | 1 | 1 (8 items) |
| Media (files) | 455 | 453 local + 2 SVG skipped |
| Featured images | 76 used | 76 local |
| Inline image refs rewritten | — | 199 refs / 41 items |
| Internal link refs rewritten | — | 394 refs / 62 items |
| SEO-image applied | — | 74 items |

Verified at migration time via the admin API: **73 posts + 14 pages + 5 categories + 3
bylines + primary menu + 453 media items** (repost list + paginated media list).

## Media verification

- `migration/migrate-media.py` uploaded all 455 source media in-memory to
  `POST /media?deduplicate=true`; 453 migrated, 2 SVG skipped, 0 errors
  (`media-map-report.txt`).
- `migration/media-reconcile-featured.py` removed 74 duplicate featured-media uploads
  and repaired the map (`uploads/` dropped by ~4 MB).
- 211 media items have captions copied from the WP `caption` field.

## Content-fidelity verification (`migration/verify-content.py`)

For each of the 73 posts + 14 pages the script checks:

- slug, title (exact `rendered` match)
- `publishedAt` == WordPress `date_gmt`
- category term assignment (exact set match)
- featured-image presence parity
- word-level content similarity between the WP rendered HTML and the EmDash Portable
  Text, ignoring Kadence `<style>`/`<script>` output and dynamic Kadence widgets
  (latest-posts/archive loops, tag clouds).

Result: **87 / 87 items clean (0 issues)** — stored in
`migration/wordpress-source/content-verification.json`.

The two pages whose raw similarity reads low are explained, not failures:

- `book-your-free-consultation` — tiny corpus (a heading + Calendly embed markers); all
  WP words are present; the extra EmDash tokens come from the Calendly widget text.
- `academy` — the page body is a dynamic latest-posts grid (its text is the auto-rendered
  excerpts/titles of the six most recent blog posts, which are themselves fully migrated).
  All static WP text is present.

A real data-loss bug was found and fixed: the first HTML→PT conversion dropped orphan
text at body level and text interleaved with inline children in containers — most visible
on gated "paywall" teaser posts (e.g. `headline-battle-which-message-turns-viewers-into-buyers`
lost "Quick answer: …" and "… to read the rest of this content."). The converter in
`migrate.py` was fixed and `repair-content.py` reconverted the 18 affected items
(17 posts + 1 page), re-applying image and link rewrites.

## Rendered-site verification

Smoke test (curl, all HTTP 200):

- `/` (homepage post list, Kiko theme)
- `/posts/confidence-vs-posthog`, `/posts/headline-battle-which-message-turns-viewers-into-buyers`
- `/pages/academy`, `/pages/home`, `/pages/experiment-test-page`, `/pages/contact-form`,
  `/pages/hire-cro-expert`, `/pages/book-your-free-consultation`
- a local media file serves HTTP 200 as `image/webp` from EmDash storage

Grep of all live content confirms the only remaining `99ways.instawp.dev` references are
the six documented intentional ones (SVG, 404/ambiguous image, three dead-slug link
targets, A/B test self-link URLs).

## Dates

- All 73 posts + 14 pages backdated to original WordPress `date_gmt` via
  `migration/backdate.py` (`publishedAt` re-publish). Spot-checked
  `confidence-vs-posthog` → 2026-09-09 and `pages/home` → 2026-04-23.

## SEO

- All 73 posts + 14 pages have `seo.title` + `seo.description` applied from Yoast
  (`migration/apply-seo.py`, 87 updated / 0 failed).
- `seo.image` applied to 74 items (all with locally-hosted featured media).

## Limitations (documented)

- 2 SVG media files could not be uploaded (EmDash allowlist); 1 remains as a hotlink in
  a page body, the others were only ever linked from content.
- 1 inline image (`2025/05/1-1024x329.jpg`) was 404 on the source clone and ambiguous
  by basename — remains a hotlink.
- 3 internal link targets (`posthog-implementation-services`,
  `a-b-testing-setup-in-shopify-with-posthog`, `posthog-a-b-testing-on-wordpress`) do not
  exist in the source snapshots — links remain pointing at the WP clone.
- WordPress media `description` is not representable in EmDash (alt + caption only).
- Interactive Kadence widgets (forms, buttons, accordions, dynamic loops, gating) are not
  recreated — content-equivalent static text/images, where present, are preserved.