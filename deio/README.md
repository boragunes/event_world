# DEIO — Deep Event Inertial Odometry (container + results)

[DEIO](https://github.com/arclab-hku/DEIO) (Guan et al., ICCV 2025, [arXiv:2411.03928](https://arxiv.org/abs/2411.03928))
is the first **monocular learning-based event–inertial** odometry: an event recurrent
network provides patch associations, fused with IMU pre-integration in a learned
differentiable-bundle-adjustment factor graph (DPVO / DEVO lineage + GTSAM).

## Faithful container
DEIO ships **no Dockerfile** — it's a conda / PyTorch-2.3.1 / CUDA-11.8 project. The
[`Dockerfile`](./Dockerfile) here follows `environment.yml` + the README build steps verbatim
(conda env → `pip install .` CUDA extensions → GTSAM Python bindings), pinning upstream commit
`47dcc27`. No source edits. Build does not need a GPU; **running does**.
```bash
deio/build.sh                       # -> event-world/deio:latest (~30-60 min)
DEVO_WEIGHTS=/path/DEVO.pth DATA=/path/UZH-FPV deio/run_deio.sh uzhfpv
```

## Results on VECtor — our run vs the DEIO paper (Table IV)
DEIO ships no VECtor eval script/config, so we reconstruct the run (`deio/prepare_vector.py` +
`deio/vector_config.yaml` + `deio/vector_eval.py`; **no DEIO source edits**) and produce **our own
trajectories**. We evaluate with **SE3 (metric)** — DEIO fuses an IMU, so its scale must be metric —
and score against the **event-camera-frame** GT (the frame DEIO estimates; `<seq>_gt.txt`).

| sequence | DEIO ours (SE3) | authors' released (SE3) | paper reports (Sim3) |
|---|---|---|---|
| corner-slow | **1.89** | 4.40 | 0.50 \* |
| desk-normal | **0.33** | 23.69 | 0.13 \* |
| sofa-fast | **0.14** | 0.48 | 0.44 \* |
| mountain-fast | **0.52** | 0.26 | 0.24 \* |
| desk-fast | 0.11 | — | *not in paper* |
| sofa-normal | 0.29 | — | *not in paper* |
| robot-normal | 0.54 | — | *not in paper* |
| robot-fast | 0.25 | — | *not in paper* |
| mountain-normal | 1.70 | — | *not in paper* |
| hdr-normal | 10.39 † | — | *not in paper* |
| hdr-fast | 0.66 | — | *not in paper* |

**\* The paper's numbers use Sim3 (`correct_scale=True`), which masks scale-broken trajectories.**
DEIO is monocular, so scale is unobservable on low-excitation sequences — the authors' *own released*
trajectories drift badly once scale-correction is off (honest SE3): corner-slow 0.57→**4.40**,
desk-normal 0.28→**23.69**. So Table IV's 0.50/0.13 are scale-correction artifacts, not metric accuracy.
Under the same honest SE3 metric our reconstruction is **more accurate than the authors' released runs
on 3/4 paper sequences**, and our trajectories are genuinely metric (Sim3≈SE3). **† hdr-normal** is
near-static → monocular scale unobservable for anyone (ours too: SE3 10.39 vs Sim3 0.97); SE3 reports it
honestly. The input pipeline is independently verified faithful (event data byte-identical to VECtor's
native HDF5, rectification = official calibration, voxel/IMU/`DEVO.pth` all the authors').
Full analysis: **[the report](../docs/validation/deio_vector.md)**.

## Layout
```
deio/
  Dockerfile  build.sh  run_deio.sh  prepare_vector.py  vector_eval.py  vector_config.yaml  README.md
  vector/<seq>/        our DEIO run: trajectory + GT + SE3 metrics + PDF/PNG plots
  vector_imu2x/<seq>/  our IMU-covariance study
```
DEIO is the original authors' work under its own license; this folder only adds containerization,
the reconstructed run harness, and evaluation glue. **No authors' trajectories are used.**
