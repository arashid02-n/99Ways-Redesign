# 99Ways v1.0 export validation

**Production date:** 2026-09-14  
**Result:** PASS  
**Scope:** approved full 99Ways wordmark and compact 99 only

## Checks performed

- Canonical master bounds, custom 9 construction, 74-unit pitch, 2-unit canonical bowl gap, pupil radius/position, and all four outlined letter placements match the approved specification.
- Editable masters contain named paths, independently movable pupils, outlined lettering, no hidden duplicates, no text/font dependency, no masks, no external references, and no raster elements.
- Eight delivery SVGs open as standalone path geometry with exact viewBoxes and exact hexadecimal fills. Transparent counters remain transparent.
- Eight PDFs have one vector-only page, the approved MediaBox, no font or image resources, and exact RGB fill values. Every PDF was rasterized independently; see `visual-proofs/vector-pdf-render-proof.png`.
- Wordmark PNGs have 1024 px or 2048 px visible-artwork width and proportional height. Compact PNGs have exact 512 or 1024 px square canvases, 75% width occupancy, undistorted geometry, and transparent surroundings.
- Standard light and dark treatments use exact role colors. One-color SVG/PDF/PNG files use pure black or pure white with the pupil structure united into the silhouette.
- Apple touch and avatar assets are opaque Warm White fields with exact Graphite and Inquiry Blue mark colors.
- Main proof, minimum-size proof, micro proof, and avatar crop proof were rendered in a browser and inspected at intended display sizes.

## Size-specific micro results

The alpha silhouette test uses a 64/255 visibility threshold on the 1x light file. Two components means the two 9s remain distinct. Blue-like pixels verify that the gaze survives rasterization.

| Target | Tested densities | Silhouette components | Component areas (px) | Gaze pixels at 1x | Result |
|---:|---|---:|---:|---:|---|
| 16px | 1x and 2x | 2 | 26 / 25 | 6 | Pass |
| 24px | 1x and 2x | 2 | 57 / 57 | 14 | Pass |
| 32px | 1x and 2x | 2 | 109 / 106 | 20 | Pass |
| 48px | 1x and 2x | 2 | 257 / 256 | 43 | Pass |

The 16/24/32/48 px micro files use documented optical spacing, counter, and pupil changes. They are derivatives of the compact master; the canonical 2-unit gap and approved pupil geometry remain unchanged.

## Usage limits established in this release

- Full wordmark: validated normal digital minimum of **180 CSS px visible artwork width**.
- Canonical compact mark: use at **64 CSS px and above**.
- At 16, 24, 32, or 48 px, use the derivative source named for that exact target size. Use the matching 2x PNG for twice-density display at the same CSS size.
- Clear space: minimum 25 design units from the visible artwork bounds.
- Print minima and material-specific reproduction remain unvalidated because no printer, substrate, or production process was part of this release.

## Proofs

- `visual-proofs/99ways-brand-assets-v1.0-proof-sheet.png`
- `visual-proofs/minimum-size-proof.png`
- `visual-proofs/micro-proof.png`
- `visual-proofs/avatar-proof.png`
- `visual-proofs/vector-pdf-render-proof.png`

## Unresolved issues

No blocking asset defect remains. Three application checks remain outside this export package:

- favicon selection and caching in the real website/browser stack;
- the avatar after upload through each platform's own image processing;
- physical print minima, CMYK/spot-color conversion, and material-specific reproduction.

White transparent files can look blank in file browsers that preview them on white. Their geometry and pure-white fill were validated on a Graphite proof field.

**Automated assertions passed:** 260  
**Automated assertions failed:** 0
