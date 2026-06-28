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

## Results on VECtor — our run, SE3 (metric)
DEIO ships no VECtor eval script/config, so we reconstruct the run (`deio/prepare_vector.py` +
`deio/vector_config.yaml` + `deio/vector_eval.py`; **no DEIO source edits**) and produce **our own
trajectories** — we **never use the authors' released `.txt` files** (mixed DEVO/DEIO provenance,
scale-ambiguous). We evaluate with **SE3 (metric)**: DEIO fuses an IMU, so it must be metric, and
Sim3 would mask scale failures.

| sequence | DEIO ours (SE3) | ESVIO ours (SE3) |
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

DEIO recovers metric scale on every excited sequence and runs robot-fast/mountain-fast where
ESVIO's init diverges. **† hdr-normal** is near-static (GT 3.1 m) → monocular scale unobservable
(raw 9.3×); **SE3 exposes it (12.67) where Sim3 would hide it (1.39)** — stereo ESVIO recovers
metric scale (0.61). Full analysis + faithful-tuning study:
**[the report](../docs/validation/deio_vector.md)**.

## Layout
```
deio/
  Dockerfile  build.sh  run_deio.sh  prepare_vector.py  vector_eval.py  vector_config.yaml  README.md
  vector/<seq>/        our DEIO run: trajectory + GT + SE3 metrics + PDF/PNG plots
  vector_imu2x/<seq>/  our IMU-covariance study
```
DEIO is the original authors' work under its own license; this folder only adds containerization,
the reconstructed run harness, and evaluation glue. **No authors' trajectories are used.**
