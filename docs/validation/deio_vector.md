# DEIO on VECtor — our run vs published, + IMU-covariance study

[DEIO](https://arxiv.org/abs/2411.03928) (deep monocular event–inertial odometry, ICCV 2025)
tops VECtor Table IV. DEIO's public repo ships **no VECtor eval script / config** (only
`davis240c.py` and `uzh-fpv.py` run out of the box), so to actually *run* DEIO on VECtor we
**reconstructed its eval path**. Everything below is scored with our own `scripts/evaluate.py`
(Sim3 / scale-corrected alignment — DEIO's own convention; MPE % = 100·ATE-RMSE / length).

## How we ran it (reconstruction — not upstream-faithful)
DEIO ships a VECtor data *loader* (`utils.load_utils.vector_evs_iterator`) + sequence splits but
not the surrounding harness. We added, with **no edits to DEIO source**:
- **`deio/prepare_vector.py`** — our VECtor rosbags → DEIO's input layout per sequence: DSEC
  `EventSlicer` event HDF5 (`x/y/p/t`,`ms_to_idx`,`t_offset`), `rectify_map_left.h5` + 4-value
  intrinsics (from VECtor's `event0` calibration via OpenCV), `tss_imgs_us`, `imu.txt`, GT, `t0`.
- **`deio/vector_config.yaml`** — DEVO VO params + the VECtor event↔IMU extrinsic (`Ti1c`) and
  IMU noise (acc 0.2 / gyr 0.05) from `esvio_VECtor_small_scale`.
- **`deio/vector_eval.py`** — mirrors upstream `uzh-fpv.py`, swapping in `vector_evs_iterator`.

Run in the faithful `event-world/deio` container on an A5000. V-I init recovers gravity
(`≈[0,0,9.81]`), confirming the extrinsic/IMU conventions. Validation: our run's numbers land in
DEIO's published regime (below).

## Results — MPE % (all 11 sequences)
| sequence | **DEIO ours** | DEIO published | ESVIO ours (SE3) |
|---|---|---|---|
| desk-normal | 0.45 | 0.34 | 0.43 |
| desk-fast | 0.11 | 0.15 | 1.67 |
| sofa-normal | 0.11 | 0.19 | 0.24 |
| sofa-fast | 0.12 | 0.50 | 2.54 |
| robot-normal | 0.46 | 0.38 | 0.87 |
| robot-fast | 0.14 | 0.17 | *init fails* |
| corner-slow | 2.29 | 1.02 | 1.95 |
| mountain-normal | 1.09 | 1.36 | 0.72 |
| mountain-fast | 0.57 | 0.26 | *init fails* |
| hdr-normal | 1.39 † | 0.71 | 0.61 |
| hdr-fast | 0.58 | 0.30 | 1.26 |
| **average** | **0.67** | 0.49 | 1.14 (9 converged) |

Single trial per sequence (the paper reports a multi-trial median — see Tuning below). Our
reconstructed run averages **0.67%** vs published **0.49%** — the same regime — beats published on
desk-fast/sofa-normal/sofa-fast/mountain-normal, and crucially runs **robot-fast (0.14)** and
**mountain-fast (0.57)**, the sequences where ESVIO's classical global-SFM init diverges.

**† hdr-normal scale caveat (important for citation):** hdr-normal is near-static (GT path only
**3.1 m over 60 s**), so there is little IMU excitation and **monocular DEIO cannot observe metric
scale** — its raw trajectory is **28.8 m (≈9× too long)**. The Sim3 (scale-corrected) alignment
removes this, so 1.39% is a **shape-only** number, consistent with the authors' own Sim3 convention
(their 0.71 is also Sim3). By contrast, **stereo ESVIO recovers metric scale on the same sequence
(0.61%, SE3)** — a genuine method difference, faithfully reported. Coverage was verified ≥97% of
the GT time span for every committed trajectory.

## Faithful tuning — none closes the systematic gaps
Only legitimate knobs were tried; anything that adds capacity/compute (e.g. `PATCHES_PER_FRAME`) is
**excluded as non-faithful**. On the worst sequence, corner-slow (2.29 vs published 1.02):
- **Multi-trial median** (the paper's own protocol): 2.28–2.36 across 5 trials → near-zero variance,
  so the gap is *not* run-to-run noise.
- **Voxel time-window `dt_ms`** (33 / 50 / 100 ms): 2.25–2.32 → no real change.
- **Keyframe-removal threshold `KEYFRAME_THRESH`** (2→12; higher ⇒ fewer, wider-baseline keyframes,
  256→41 kept): 2.35→2.23, monotonic but marginal — for this slow sequence sparser wide-baseline
  keyframes triangulate slightly better, not enough to matter.
- **IMU covariance ×2** (`deio/vector_config_imu2x.yaml`): **net-negative**, avg 0.65→1.02%
  (robot-normal 0.46→**3.00** worst); only corner-slow/mountain-normal marginally helped. DEIO's
  default IMU sigmas are well-matched.

**Conclusion:** no faithful config change closes the corner-slow (or mountain-fast / hdr-fast) gap —
it is inherent to reconstructing the authors' exact event-representation / rectification pipeline,
not a tunable. We report the **authors' default config** as the faithful result and do not tune to
chase the paper.

## Provenance note
`deio/vector/<seq>/` holds DEIO's **published** trajectories (Sim3-evaluated). `deio/vector_ourrun/`
and `deio/vector_ourrun_imu2x/` hold **our own runs** (reconstruction). All three use the same
`evaluate.py` + VECtor GT.
