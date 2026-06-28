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

## Results on VECtor — DEIO's published trajectories
**Important provenance:** DEIO's public code has **no VECtor eval script / config** (only
`davis240c.py` and `uzh-fpv.py` are runnable). It *does* publish the authors' own VECtor
**trajectories**. So `deio/vector/<seq>/` holds **DEIO's published trajectories**, evaluated
against our VECtor ground truth with the **same evo pipeline** — using **Sim3 (scale-corrected)
alignment**, which is DEIO's own convention (`correct_scale=True` in their eval notebook). These
are *not* our run. We **also ran DEIO on VECtor ourselves** by reconstructing the missing eval
path (`deio/prepare_vector.py` + `deio/vector_eval.py` + `deio/vector_config.yaml`) — results in
`deio/vector_ourrun/` and **[the full report](../docs/validation/deio_vector.md)**: our run
averages **0.65% MPE** vs published 0.50% on the 9 sequences with event data, and a 2×
IMU-covariance study (`deio/vector_ourrun_imu2x/`) found inflating it net-negative (0.65→1.02%).

### DEIO (Sim3) vs our ESVIO (SE3) on VECtor — MPE %
| sequence | ESVIO (SE3, our run) | DEIO (Sim3, published) |
|---|---|---|
| desk-normal | 0.43 | **0.34** |
| desk-fast | 0.24 | **0.15** |
| sofa-normal | 0.24 | **0.19** |
| sofa-fast | 2.54 | **0.50** |
| robot-normal | 0.87 | **0.38** |
| robot-fast | *init fails* | **0.17** |
| corner-slow | 1.95 | **1.02** |
| mountain-normal | **0.72** | 1.36 |
| mountain-fast | *init fails* | **0.26** |
| hdr-normal | 3.62 | **0.71** |
| hdr-fast | 1.26 | **0.30** |

DEIO wins **10/11** (ESVIO only on mountain-normal), and crucially handles the **fast** sequences
where ESVIO's classical init diverges. Note the alignment differs (DEIO Sim3 / scale-corrected vs
ESVIO SE3 / metric) because each paper reports its own convention — see
[the report](../docs/validation/deio_vector.md).

## Layout
```
deio/
  Dockerfile  build.sh  run_deio.sh  README.md
  vector/<seq>/    DEIO published trajectory + our GT + Sim3 metrics + PDF/PNG plots
  uzhfpv/<seq>/    our faithful container run (validates reproduction vs the paper)
```
DEIO is the original authors' work under its own license; this folder only adds containerization
and evaluation glue.
