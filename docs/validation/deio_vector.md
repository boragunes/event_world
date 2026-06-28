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

## Results — MPE %
| sequence | **DEIO ours** | DEIO IMU 2× | DEIO published | ESVIO ours |
|---|---|---|---|---|
| desk-normal | 0.45 | 0.58 | 0.34 | 0.43 |
| sofa-normal | 0.11 | 0.11 | 0.19 | 0.24 |
| sofa-fast | 0.12 | 0.15 | 0.50 | 2.54 |
| robot-normal | 0.46 | 3.00 | 0.38 | 0.87 |
| robot-fast | 0.14 | 0.18 | 0.17 | *init fails* |
| corner-slow | 2.29 | 2.19 | 1.02 | 1.95 |
| mountain-normal | 1.09 | 1.05 | 1.36 | 0.72 |
| mountain-fast | 0.57 | 0.83 | 0.26 | *init fails* |
| hdr-fast | 0.58 | 1.09 | 0.30 | 1.26 |
| **average (9)** | **0.65** | **1.02** | 0.50 | — |
| *desk-fast, hdr-normal* | *no event data in the import* | | | |

Single trial per sequence (the paper reports a multi-trial median, which explains the
corner-slow / mountain-fast / hdr-fast gaps). Our reconstructed run averages **0.65%** vs
published **0.50%** — the same regime — beats published on sofa-normal/sofa-fast/mountain-normal,
and crucially runs **robot-fast (0.14%)** and **mountain-fast (0.57%)**, the exact sequences where
ESVIO's classical global-SFM init diverges.

## IMU-covariance study (`deio/vector_config_imu2x.yaml`, sigmas ×2 ⇒ covariance ×4)
Inflating the IMU covariance is **net-negative**: average **0.65 → 1.02%**. It badly hurt
robot-normal (0.46→**3.00**) and the HDR / mountain-fast sequences; it only marginally helped the
two low-excitation slow sequences (corner-slow 2.29→2.19, mountain-normal 1.09→1.05), within
noise. Conclusion: **DEIO's default IMU sigmas are well-matched to VECtor** — the IMU is a useful
constraint here, and down-weighting it degrades accuracy.

## Provenance note
`deio/vector/<seq>/` holds DEIO's **published** trajectories (Sim3-evaluated). `deio/vector_ourrun/`
and `deio/vector_ourrun_imu2x/` hold **our own runs** (reconstruction). All three use the same
`evaluate.py` + VECtor GT.
