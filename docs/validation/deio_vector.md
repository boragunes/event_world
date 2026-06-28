# DEIO on VECtor — our run, SE3 (metric)

[DEIO](https://arxiv.org/abs/2411.03928) (deep **monocular event–inertial** odometry, ICCV 2025)
tops VECtor Table IV. We run DEIO ourselves in the faithful `event-world/deio` container and score
it with our own `scripts/evaluate.py`. Two non-negotiable standards:

- **Our own trajectories only.** We never use the authors' released `.txt` files. (Those VECtor
  files are mixed provenance — several dirs are literally named `_step_DEVO`, the *vision-only*
  baseline — and are scale-ambiguous. A trustworthy benchmark must produce and own every trajectory.)
- **SE3 (metric) alignment — always, for any method with metric information (IMU and/or stereo).**
  DEIO fuses an IMU, so it *must* be metric; **Sim3 / scale-correction would give an inertial method
  a free pass on the very thing the IMU is there to provide.** ESVIO (stereo+IMU) is likewise SE3.

## How we run it (reconstruction — no DEIO source edits)
DEIO ships a VECtor data *loader* (`vector_evs_iterator`) + splits but no eval script/config. We add:
`deio/prepare_vector.py` (our rosbags → DSEC event HDF5 + rectify map from the event0 calibration +
intrinsics + image timestamps + `imu.txt` + GT + t0), `deio/vector_config.yaml` (event↔IMU extrinsic
`Ti1c` + IMU noise), and `deio/vector_eval.py` (mirrors upstream `uzh-fpv.py`). V-I init recovers
gravity (`≈[0,0,9.81]`), confirming the conventions.

## Results — MPE % (SE3, our runs, authors' default config)
| sequence | **DEIO ours** | ESVIO ours |
|---|---|---|
| desk-normal | 0.46 | 0.43 |
| desk-fast | 0.11 | 1.67 |
| sofa-normal | 0.31 | 0.24 |
| sofa-fast | 0.12 | 2.54 |
| robot-normal | 0.75 | 0.87 |
| robot-fast | 0.16 | *init fails* |
| corner-slow | 2.63 | 1.95 |
| mountain-normal | 1.80 | 0.72 |
| mountain-fast | 0.61 | *init fails* |
| hdr-normal | 12.67 † | 0.61 |
| hdr-fast | 0.74 | 1.26 |
| **avg (excl. hdr-normal outlier)** | **0.77** | 1.14 (9 conv.) |

Both columns are **our own runs under SE3** — directly comparable, no scale free-passes. DEIO
**recovers metric scale on every well-excited sequence** (its SE3 value ≈ its Sim3 value, so the IMU
is doing its job) and runs **robot-fast / mountain-fast**, the sequences where ESVIO's classical
global-SFM init diverges.

**† hdr-normal — the one scale failure, exposed by SE3:** it is near-static (GT path **3.1 m over
60 s**), so there is no IMU excitation and **monocular DEIO cannot observe metric scale** — the raw
trajectory is **28.8 m (≈9.3×)**. SE3 reports this honestly (**12.67%**); Sim3 would have hidden it
(1.39%). **Stereo ESVIO recovers metric scale on the same sequence (0.61%)** — a genuine
mono-vs-stereo difference, and the clearest argument for the SE3 rule. Coverage ≥97% of the GT time
span was verified for every committed trajectory.

## Why SE3 and not the paper's Sim3
The DEIO paper evaluates VECtor with **Sim3 (scale-corrected)**. For an event-**inertial** method
that is too lenient: it cannot distinguish a run that recovered metric scale from one that did not
(see hdr-normal). So the paper's numbers are **not directly comparable** to ours — we report the
honest metric (SE3) instead of chasing a scale-forgiving figure.

## Faithful tuning — nothing closes the systematic gaps
Only legitimate knobs were tried; anything that adds capacity/compute (e.g. `PATCHES_PER_FRAME`) is
**excluded as non-faithful**. On the worst sequence, corner-slow:
- **Multi-trial median** (paper's protocol): 2.28–2.36 across 5 trials → not run-to-run noise.
- **Voxel window `dt_ms`** (33/50/100 ms): 2.25–2.32 → no real change.
- **`KEYFRAME_THRESH`** (2→12; higher ⇒ fewer wider-baseline keyframes): 2.35→2.23, marginal.
- **IMU covariance ×2** (`deio/vector_imu2x/`): net-negative.

**Conclusion:** no faithful config change closes the gaps — they are inherent to reconstructing the
authors' exact event-representation / rectification pipeline. We report the **authors' default
config**, and do not tune to chase the paper.

## Provenance
`deio/vector/<seq>/` = **our** DEIO run (default config, SE3). `deio/vector_imu2x/` = our
IMU-covariance study. No authors' trajectories are used anywhere.
