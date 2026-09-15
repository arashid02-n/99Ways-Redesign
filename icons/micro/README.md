# Micro-size compact derivatives

The canonical compact master keeps the approved 2-unit gap, 20-unit counter radius, 9-unit pupil radius, and 14-unit pupil offset. At 16-48 px those relationships become sub-pixel details. The files in this folder are deliberate size-specific derivatives; they never replace the canonical master.

| Target | Pair gap | Counter radius | Pupil radius | Pupil offset | Artwork occupancy |
|---:|---:|---:|---:|---:|---:|
| 16 px | 24 units | 22 units | 10 units | 16 units | 75% |
| 24 px | 18 units | 21 units | 9.5 units | 15 units | 75% |
| 32 px | 12 units | 21 units | 9 units | 15 units | 78% |
| 48 px | 8 units | 20.5 units | 9 units | 14.5 units | 80% |

The increasing pair gap preserves two separate bowls. The slightly larger counters preserve negative space. The 16/24 px pupils are enlarged and moved outward to retain the downward gaze and body separation. Both pupils remain identical and aligned. No tail, silhouette, or gaze direction was redesigned.

Use the SVG named for the exact target size as the source. The `1x.png` is the actual target-pixel export; `2x.png` contains twice the pixels for the same intended CSS/display size. Do not scale the 16 px derivative up for larger icons or substitute these files for the full-size compact master.
