# EmDash Capability Mapping

What EmDash can and cannot represent from the WordPress source, based on verifying the
actual EmDash implementation rather than assuming feature parity. This bounds the
migration's known limitations and the Phase 2 design work.

## Capabilities verified against the implementation

| Capability | EmDash support | Used by 99Ways |
|---|---|---|
| Collections (posts, pages) | Yes — drafts/revisions/seo/scheduling/search per collection | posts, pages |
| Portable Text rich content | Yes — headings, lists, blockquote, code, marks, inline images | All bodies |
| Media library | Yes — upload, alt, caption; **no `description` field** | 453 files, alt+caption |
| Uploaded file types | Allowlist: png/jpeg/gif/webp/avif/video/audio/pdf — **no SVG** | 2 SVG blocked |
| Upload size limit | 50 MB (`DEFAULT_MAX_UPLOAD_SIZE`) | No files near limit |
| Featured image | Yes — `featured_image` field per item | 76 posts/pages |
| Taxonomy | Yes — terms, no hierarchies used | 5 categories |
| Bylines | Yes — guest credits (no CMS users) | 3 authors |
| Navigation menus | Yes — `primary` menu, ordered items | 1 menu / 8 items |
| SEO per item | Yes — `seo.title` / `description` / `image` / `canonical` / `noIndex` | Yoast titles/descriptions + local images |
| Dates | Yes — `publishedAt` backdating | 87 items |
| Site settings | Title, tagline, favicon, social, SEO defaults, robots.txt | title/tagline/favicon |
| Draft/publish workflow | Yes — draft revisions + published snapshots | Used during migration |
| Markdown ↔ Portable Text | Yes — markdown conversion supported by the content API | Used for spot-checks |

## Not represented (and why)

| WordPress feature | EmDash | Why dropped / not migrated |
|---|---|---|
| Kadence interactive widgets (forms, buttons, accordions, spacers) | No equivalent | Interaction behaviour is not content; static text/images preserved |
| Kadence dynamic loops (latest-posts, archive grids, tag clouds) | No equivalent | Live queries; duplicated/migrated content exists as items themselves |
| Gating / paywall overlays | No equivalent | Notice + links preserved as text |
| WooCommerce store behaviour | No equivalent | Pages migrated as static content only |
| Media `description` | No field | alt + caption only |
| SVG uploads | Allowlist blocks | Cannot be registered |
| WordPress site settings endpoint | — | Source returns 401 without credentials |

Items in "Not represented" are documented in `mapping.md` (decisions) and
`verification.md` (verification + remaining hotlinks), and remain candidates for Phase 2
design work in the Astro layer rather than CMS conversions.