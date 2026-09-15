# 99Ways — Selected logo specification

**Preview version 1.0 · 13 September 2026**

The user selected **S2 Aggressive Tightening** and **02 Colored Gaze**, combined with 02A Noticing, IBM Plex Mono, the accepted five-color palette, downward gaze, and future shared up/down motion. This document supersedes the earlier S1 recommendation and alternative creative forks. It specifies the definitive combined preview. The v1.0 asset release implements it without changing the approved design.

## Geometry and typography

Use a nominal cap height of 100 units. The cap line is vertical zero; the baseline is 100; vertical coordinates increase downward.

Each custom 9 has an outer circular bowl of radius 36, centered at horizontal 36, vertical 35. The bowl overshoots the cap line by 1 unit. The counter is a concentric circle of radius 20. Retain the straight-sided tail descending left at 35 degrees from vertical. Its upper corners are approximately (43.4895,55.6488) and (65.4895,55.6488), and its baseline corners are (12.4344,100) and (34.4344,100). Unite bowl and tail, then subtract the counter.

The pupil is a complete circle of radius 9. Its center is 14 units from the bowl center at 25 degrees below the rightward horizontal: approximately (48.6883,40.9167). It overlaps the body by 3 units along that radius. Keep it as a separate blue circle over the counter-cut body, with no duplicate static pupil underneath.

Translate the second complete 9 exactly 74 units right. This gives the accepted **2-unit gap** between the circular heads. The pair’s visible width is 146 units. Do not widen that gap in the full-size master. A later micro derivative is a separate decision.

Use the exact **IBM Plex Mono Semibold 600** upright outlines for W, a, y, s. Scale the font’s nominal cap height to 100 and place its baseline at 100. Preserve native outline widths, lowercase heights, and descenders. Do not horizontally scale, enable automatic kerning, or use fixed character advances. Zero visible bounding-box gaps do not mean all glyph contours touch.

| Element | Visible left position | Visible width |
|---|---:|---:|
| First 9 | 0 | 72 |
| Second 9 | 74 | 72 |
| W | 156.0000 | 80.8023 |
| a | 236.8023 | 72.9226 |
| y | 309.7249 | 77.6504 |
| s | 387.3754 | 68.3381 |

Accepted gap sequence: **9–9 = 2; 9–W = 10; W–a = 0; a–y = 0; y–s = 0**. The last three are distances between extreme visible bounds, not added tracking.

The full wordmark’s visible bounds are approximately **455.7135 units wide × 129.6533 units high**, from vertical −1 to 128.6533. The compact pair is 146 × 101 units. Preserve these proportions. Clear space belongs outside those bounds.

## Color assignment

| Part | Light treatment | Dark treatment |
|---|---|---|
| Both 9 bodies and Ways | Graphite #292B2A | Warm White #F4F3EF |
| Both pupils | Inquiry blue #3558B8 | Inverse inquiry blue #A6BAFF |
| Preview field | Warm White #F4F3EF | Graphite #292B2A |

The fields above describe presentation and usage; the transparent masters keep the counters transparent. Use the local field to choose a treatment. Do not invert the entire artwork with a color filter.

The established core palette is Graphite #292B2A, Warm White #F4F3EF, Muted #676B65, Inquiry blue #3558B8, and Performance green #147D40. The inverse role tones #A6BAFF, #B5B8B1, and #6BD98D are retained adaptations. Green and muted gray do not enter the selected logo. No connecting bridge, colored tails, point in a, extra keyline, or pupil halo is included.

In one color, give bodies, pupils, and letters the same ink. The geometry remains unchanged. Static production export may unite touching same-color shapes; the editable source retains separate pupils for motion.

## Motion continuity

The accepted concept is two pupils moving together up and down and returning to the downward rest. Preserve the radius-14 arc between angles +25 and −25 degrees relative to the rightward horizontal. The bodies, tails, type, and spacing stay fixed. Pupils keep their theme-appropriate blue fill. The earlier 320 ms movement / 240 ms hold / 320 ms return remains a reference rather than a final interaction specification. The final preview is static; no new animation asset is generated.

## Source and validation boundary

Font source: [IBM Plex Mono TTF](font-license/IBMPlexMono-SemiBold.ttf), with its [OFL license](font-license/OFL.txt).

SHA-256 fingerprint: d3c38e55c78f5b0f28009fddba4834ec503278936a5986032424c9bd2d23aa46.

See [validation](../validation/export-checks.md) for rendered checks and the [persistent production tracker](../README.md) for provisional usage limits, required exports, implementation dependencies, and progress. The v1.0 export validation certifies the delivered static vectors, rasters, favicon files, touch icon, and avatar. Real website integration, physical print minima, and an animated component remain outside this release.
