# DEIO on VECtor — our run vs the DEIO paper (Table IV)

[DEIO](https://arxiv.org/abs/2411.03928) (deep **monocular event–inertial** odometry, ICCV 2025).
We run DEIO ourselves in the faithful `event-world/deio` container and score it with our own
`scripts/evaluate.py`, comparing **only to the DEIO paper's own published numbers** (Table IV).
Two non-negotiable standards:

- **Our own trajectories only.** We never use the authors' released `.txt` files (mixed provenance —
  several are the `_step_DEVO` *vision-only* baseline — and scale-ambiguous). Every estimated
  trajectory here is our own run.
- **SE3 (metric) alignment.** DEIO fuses an IMU, so it must be metric; Sim3/scale-correction would
  give an inertial method a free pass on scale.

## How we run it (reconstruction — no DEIO source edits)
DEIO ships a VECtor data *loader* (`vector_evs_iterator`) + splits but no eval script/config. We add
`deio/prepare_vector.py` (our rosbags → DSEC event HDF5 + rectify map from the event0 calibration +
intrinsics + image timestamps + `imu.txt` + GT), `deio/vector_config.yaml` (event↔IMU extrinsic +
IMU noise), `deio/vector_eval.py` (mirrors upstream `uzh-fpv.py`). V-I init recovers gravity.

## Results — MPE % (SE3 metric, our run)
| sequence | **DEIO ours (SE3)** | DEIO paper (Table IV) |
|---|---|---|
| corner-slow | 2.63 | **0.50** |
| desk-normal | 0.46 | **0.13** |
| sofa-fast | 0.12 | **0.44** |
| mountain-fast | 0.61 | **0.24** |
| desk-fast | 0.11 | *not in paper* |
| sofa-normal | 0.31 | *not in paper* |
| robot-normal | 0.75 | *not in paper* |
| robot-fast | 0.16 | *not in paper* |
| mountain-normal | 1.80 | *not in paper* |
| hdr-normal | 12.67 † | *not in paper* |
| hdr-fast | 0.74 | *not in paper* |

The DEIO paper's Table IV reports **only the four small-scale sequences above** (plus large-scale
corridors/units we don't have; paper avg 0.44%). On those four, we **match/beat on sofa-fast
(0.12 vs 0.44)** but sit **2–5× higher on corner-slow, desk-normal, mountain-fast** — the
**reconstruction gap**: our event-HDF5 / rectification pipeline is not the authors' exact (unreleased)
one. The gap holds under Sim3 too (corner-slow 2.29, desk-normal 0.45, mountain-fast 0.57), so it is
**not an alignment artifact**. The paper's Table IV alignment is unspecified ("aligning the whole
ground truth trajectory"); the authors' notebook uses Sim3 — we report SE3 (metric) as our standard.

**† hdr-normal (not in the paper) — scale failure, exposed by SE3:** near-static (GT path **3.1 m /
60 s**) ⇒ no IMU excitation ⇒ **monocular DEIO cannot observe metric scale** (raw 28.8 m, ≈9.3×). SE3
reports it honestly (12.67%); Sim3 would hide it (1.39%). Coverage ≥97% of the GT span was verified
for every committed trajectory.

## Faithful tuning — nothing closes the gaps
Only legitimate knobs tried; anything that adds capacity/compute (e.g. `PATCHES_PER_FRAME`) is
**excluded as cheating**. On corner-slow (2.63 SE3 / 2.29 Sim3 vs paper 0.50):
- **Multi-trial median** (paper's protocol): 2.28–2.36 across 5 trials → not run-to-run noise.
- **Voxel window `dt_ms`** (33/50/100 ms): 2.25–2.32 → no real change.
- **`KEYFRAME_THRESH`** (2→12; higher ⇒ fewer, wider-baseline keyframes): 2.35→2.23, marginal.
- **IMU covariance ×2** (`deio/vector_imu2x/`): net-negative.

**Conclusion:** no faithful config change closes the gap to the paper — it is inherent to
reconstructing the authors' exact pipeline. We report the **authors' default config** and do not
tune to chase the paper.

## Provenance
`deio/vector/<seq>/` = **our** DEIO run (default config, SE3). `deio/vector_imu2x/` = our
IMU-covariance study. No authors' trajectories are used anywhere.
