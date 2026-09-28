# FAR-03A synthetic event manifest

Frozen SHA-256: `a1f1cf7f113f65f4f0044d0c856a1f0133f277a3cdc750c8f3897881030ca22b`.

Full compact geometric range/score/support curves and message-count transitions proposed nonuniform encounters; selected XYZ BEV/front/spherical figures reviewed. Organizer order identifies scenario types; no equal-duration segmentation.

Conservative encounter windows including uncertain transitions, not certified continuous object visibility. Overlaps expected. Start/end uncertainty can be tens of frames; do not infer per-frame ground truth from a window.

Split trailing nonzero message suffix at20 m forward gaps for selected review only. Concurrent objects exist. Source order never enters detector features, score or core behavior.

| Event | Scenario | Approximate window | Reviewed frames | Observed range (m) | Final prior | Confidence |
|---|---|---|---|---|---|---|
| 1 | 2 x 2 m center | 0–233 | 0, 205 | 24.1–98.7 | DETECT | high |
| 2 | 0.3 x 0.3 m center | 205–373 | 304, 350, 366 | 8.5–108.9 | DETECT | moderate |
| 3 | 0.3 x 0.3 m on rail | 304–428 | 370, 381, 405, 412 | 26.7–100.5 | DETECT | moderate |
| 4 | 0.3 x 0.3 m inside edge | 350–483 | 427, 440, 462 | 35.0–99.1 | DETECT | high |
| 5 | 0.3 x 0.3 m outside | 405–536 | 481, 493, 515, 525 | 15.7–99.5 | IGNORE | high |
| 6 | 2 x 2 m inside edge | 440–585 | 532, 542, 565, 579 | 8.7–104.7 | DETECT | high |
| 7 | 2 x 2 m outside | 493–638 | 585, 594, 615, 630 | 7.7–99.9 | IGNORE | high |
| 8 | 2 x 2 m above | 542–685 | 632, 640, 663, 679 | 11.4–102.4 | IGNORE | moderate |
| 9 | 2 x 0.2 m low across rails | 615–750 | 686, 704, 725 | 33.8–99.9 | DETECT | high |
| 10 | approximately 0.05 m hanging | 704–807 | 754, 763, 785 | 36.8–72.6 | DETECT | moderate |

Background diagnostic frames:808–1509 (702 frames). They are a provisional mostly-empty proxy;1224 remains included despite a point-count anomaly.

Exact per-frame target recall and exact maximum range cannot be established from compact unlabelled components alone. Selected verified distances are lower bounds on maximum detectable distance; first verified frame is an upper bound on actual first detection.

Review notes:

1. Regular broad transverse panel. Bag begins with it already near99 m; no pre-onset measurement. [Far/closer evidence](figures/synthetic_events/event_01_far_proposal_split_00000.png).

2. Far singleton cannot verify dimensions; the closer regular small surface and organizer order support identity. Absolute far lateral coordinate shifts on a curve. [Far/closer evidence](figures/synthetic_events/event_02_far_proposal_split_00304.png).

3. Small surface changes apparent height along approach. Organizer on-rail identity uses sequence prior plus near review; far placement is not a gauge label. [Far/closer evidence](figures/synthetic_events/far_or_transition_370_00370.png).

4. Small regular surface near right edge; sampled far width/height underresolve nominal dimensions. [Far/closer evidence](figures/synthetic_events/far_or_transition_427_00427.png).

5. Small surface left of track. Near35 m intersects estimated gauge, but near15.7 m is outside: preserve this confirmation discrepancy. [Far/closer evidence](figures/synthetic_events/far_or_transition_481_00481.png).

6. Two visible faces of a large object near right edge; do not merge another object100 m farther into its annotation. [Far/closer evidence](figures/synthetic_events/event_06_far_100_00532.png).

7. Two faces of a large left-side object; later near outside geometry supported. [Far/closer evidence](figures/synthetic_events/far_or_transition_585_00585.png).

8. Elevated large object. Organizer ABOVE is a prior, not proven by current gauge: near11 m sampled bounds intersect current clearance. Do not relabel to improve correctness. [Far/closer evidence](figures/synthetic_events/event_08_far_100_00632.png).

9. Thin transverse low surface; at99 m only one horizontal row, closer review resolves low height. [Far/closer evidence](figures/synthetic_events/additional_686_00686.png).

10. Intermittent extremely sparse vertical returns, zero sampled width. No trailing object cue in reviewed747/750/754 frames; at763 cue overlaps a much wider natural component. Physical0.05 m width is organizer prior, not resolved XYZ measurement. [Far/closer evidence](figures/synthetic_events/event_10_far_90_00754.png).

The ten identities are mapped and approximate windows frozen. This is not a dense benchmark annotation. No boundaries will move after metric results. The detector never imports this file.
