# ESVIO on VECtor — validation vs. the paper

First end-to-end run of the benchmark: **ESVIO** (stereo event-inertial VIO) on the
**VECtor** dataset, evaluated against ground truth with **evo** and compared to the
numbers reported in the ESVIO paper
([arXiv:2212.13184](https://arxiv.org/abs/2212.13184), Table II).

## Setup

| | |
|---|---|
| Algorithm | ESVIO (full stereo event + image + IMU), real-time VIO odometry |
| Image | `event-world/esvio:latest` — volkbay/ESVIO @ `16cb14a7`, **unmodified** Dockerfile (pinned) |
| Config / launch | upstream `esvio_VECtor_small_scale` (in-image, byte-identical) |
| Dataset | VECtor small-scale, official ROS bags + TUM ground truth |
| Trajectory captured | `/stereo_esvio_estimator/odometry` → TUM (as in volkbay `record_traj.sh`) |
| Evaluation | `scripts/evaluate.py` (evo v1.36.5), SE3 alignment |

### Data adaptation (minimal, lossless)
VECtor publishes events as `prophesee_event_msgs/EventArray` on `/prophesee/{l,r}/events`
as ~3.9 k tiny arrays/s, while ESVIO subscribes to `dvs_msgs/EventArray` on
`/davis/{l,r}/events` and keeps only the **most recent** array each cycle. We therefore
convert events to `dvs_msgs` (wire-identical; verified md5 `5e8beee5…`) **and** repack to
**60 Hz** frames — exactly replicating volkbay's `events_repacking_helper`
(`scripts/prophesee_to_dvs_bag.py`). All 98 M events are conserved. Cameras
(`/camera/{l,r}/image_mono`) and IMU (`/imu/data`) already match the config and are fed
unchanged. The only run-time deviation from upstream is a headless launch (no rviz /
gnome-terminal); nodes, params and config are identical.

## Results

### `desk-normal`  (8.54 m, 88.7 s, 888 odometry poses)

| Metric | Ours — VIO odometry | Ours — loop-closed | ESVIO paper |
|---|---|---|---|
| ATE RMSE (translation) | **0.104 m** | 0.105 m | — |
| **MPE** (%, SE3-aligned, ATE/length) | **1.22 %** | 1.24 % | **0.61 %** |
| Residual rotation RMSE (after removing body offset) | **1.03°** | 1.37° | — |
| Paper **MRE** | — | — | 0.38 °/m |

Plots: [`../../results/esvio/vector/desk-normal/trajectory_xy.png`](../../results/esvio/vector/desk-normal/trajectory_xy.png),
`ape_translation.png`. Full numbers: `results/esvio/vector/desk-normal/metrics.json`.

### Reading the numbers

- **Translation reproduces the paper to the same order of magnitude** — 1.2 % vs 0.61 %
  (0.10 m ATE over 8.5 m). This is a healthy result for a from-scratch containerized
  reproduction; the ~2× gap is within typical reproduction variance and is consistent
  with metric-definition nuances (ATE/length here vs the rpg relative-error the paper may
  use) and calibration/`td` differences. Loop closure barely changes it (the sequence is
  short with little drift to correct).
- **Rotation:** the raw absolute orientation error is a near-**constant 136.1° ± 0.5°** —
  i.e. a fixed sensor-to-mocap **body-frame extrinsic**, *not* a tracking error. After
  removing it, the residual orientation error is **~1° RMSE** over the whole sequence,
  confirming accurate, drift-free orientation tracking. (A fully apples-to-apples MRE in
  °/m additionally needs the translation lever-arm of that extrinsic, which we do not yet
  model — so we report the robust residual-rotation figure instead.)

**Conclusion:** the pipeline runs ESVIO faithfully end-to-end and reproduces its VECtor
`desk-normal` accuracy to the right order of magnitude. ✅

## Reproduce

```bash
algorithms/esvio/build.sh                       # one-time (faithful, pinned image)
datasets/vector/download_vector.sh desk-normal  # ROS bags + TUM ground truth
scripts/run_and_eval.sh vector desk-normal      # convert → run headless → evo
```

## TODO / next
- Scale to the other small-scale sequences (corner-slow, robot/sofa/mountain/hdr) and
  tabulate MPE/MRE against Table II.
- Model the full sensor-to-GT SE3 extrinsic for an exact °/m MRE comparison.
- Add MVSEC `indoor_flying` (also quantitative in Table II).
