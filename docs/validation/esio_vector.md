# ESIO on VECtor — the event-only variant of ESVIO

End-to-end **ESIO** — ESVIO's **event-only** variant (stereo events + IMU, **no images**) — on the
**VECtor** small-scale sequences. Same container, same config, same evaluation as our
[ESVIO run](esvio_vector.md); the only change is dropping the image front-end. The ESVIO authors
report ESIO only on their HKU dataset (Table I), **not on VECtor**, so this is new coverage.

Metric = **MPE %** = 100 × ATE-translation-RMSE / length, **SE(3)** (metric) alignment — ESIO is
stereo + IMU, so it is metric (no scale correction).

## Setup
- Same image `event-world/esvio:latest` (volkbay/ESVIO, pinned, unmodified).
- Launch `esvio/launch/esio_VECtor_headless.launch`: upstream `stereo_event_tracker` +
  `stereo_esio_estimator` + `pose_graph`, **no `stereo_image_tracker`**. Odometry topic
  `/stereo_esio_estimator/odometry`. No source edits.
- **Identical config to the ESVIO run** (`FIX_CALIB`, same IMU-noise model) — uniform methodology, no
  per-sequence tuning. Playback feeds only the stereo **event** bags + IMU (no camera bags).
- Run with `esvio/run_and_eval_esio.sh <seq>`.

## Results — ESIO (event-only) vs ESVIO (event + image + IMU)

| sequence | ESVIO (E+F+I) | ESIO (E+I) | outcome |
|---|---|---|---|
| sofa-normal | 0.24 % | **0.89 %** | ESIO ok, ×3.7 worse |
| mountain-normal | 0.72 % | **1.03 %** | ESIO ok, ×1.4 worse |
| desk-normal | 0.43 % | **4.23 %** | ESIO ok, ×9.9 worse |
| corner-slow | 1.95 % | **10.57 %** | ESIO ok, ×5.4 worse |
| hdr-normal | 0.61 % | **10.94 %** | ESIO ok, ×18 worse |
| robot-normal | 0.87 % | ✗ 111.5 % | ESIO **diverged** |
| desk-fast | 1.67 % | ✗ *(init)* | ESIO **failed to init** (0 poses) |
| hdr-fast | 1.26 % | ✗ *(init)* | ESIO **failed to init** (0 poses) |
| sofa-fast | 2.54 % | ✗ *(init)* | ESIO **failed to init** (7 poses) |
| robot-fast | ✗ 6054 % | ✗ *(init)* | **both fail** (ESVIO diverges, ESIO no-init) |
| mountain-fast | ✗ 7801 % | ✗ *(init)* | **both fail** (ESVIO diverges, ESIO no-init) |

Average over the 5 sequences where ESIO succeeds: **ESIO 5.53 %** vs **ESVIO 0.79 %**.
(Per-sequence `status.json` + `metrics.json` under `esvio/vector-esio/<seq>/`.)

## Findings
1. **Dropping images costs 1.4–18× accuracy** on the sequences where ESIO works. Stereo events + IMU
   still give metric scale (verified: the desk-normal gap is drift, not scale — SE3 4.22 % ≈ Sim3
   3.94 %), but the classical event feature front-end tracks far less stably than image features.
2. **ESIO fails on *every* fast sequence** (desk-fast, hdr-fast, sofa-fast, robot-fast, mountain-fast).
   The logs show the event-feature global-SFM init collapsing under fast motion:
   `global SFM failed` → degenerate `estimated scale: 0.02` → `little feature 0`. The event tracker
   cannot hold correspondences at that motion, so the estimator never initialises.
3. **This is the opposite of the intuition** that an event-only front-end would be more robust to fast
   motion: on VECtor the **images are what carry ESVIO through the fast sequences**
   (ESVIO does desk-fast/hdr-fast/sofa-fast fine — 1.3–2.5 %). ESIO does **not** rescue the two
   sequences where ESVIO itself diverges (mountain-fast, robot-fast) — the SFM-style init needing
   parallax is a **shared** weak point of both variants.

**Takeaway:** ESIO is strictly worse than ESVIO on VECtor — it neither matches ESVIO's accuracy on the
normal sequences nor recovers the fast-motion failures. The event-only front-end (classical ARC*-style
tracking + VINS global-SFM init) is the bottleneck; this is exactly the gap that learned event
front-ends (DEVO/DEIO) close. All results use the uniform ESVIO config — no per-sequence tuning
(faithful-benchmark principle: tuning init per fast sequence would be cheating).

## Reproduce
```bash
esvio/run_and_eval_esio.sh desk-normal      # one sequence
# all 11: for s in corner-slow robot-normal robot-fast desk-normal desk-fast \
#   sofa-normal sofa-fast mountain-normal mountain-fast hdr-normal hdr-fast; do
#   esvio/run_and_eval_esio.sh "$s"; done
python3 esvio/compare_esio_esvio.py         # the table above
```
