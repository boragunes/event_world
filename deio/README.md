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
are *not* our run. The `uzhfpv/` folder (our actual container run) is the faithful reproduction.

### ESVIO vs DEIO on VECtor — MPE %, **both under DEIO's exact logic**
Sim3 align + MPE = mean(APE)/length, `max_diff=1` (`scripts/compare_deio_logic.py`).
`FAIL` = ESVIO estimate collapsed (Sim3 would otherwise mask the divergence).

| sequence | ESVIO (our run) | DEIO (published) |
|---|---|---|
| desk-normal | 0.38 | **0.30** |
| desk-fast | 0.22 | **0.14** |
| sofa-normal | 0.22 | **0.16** |
| sofa-fast | 0.87 | **0.46** |
| robot-normal | 0.39 | **0.34** |
| robot-fast | **FAIL** | **0.15** |
| corner-slow | 1.56 | **0.83** |
| mountain-normal | **0.52** | 0.76 |
| mountain-fast | **FAIL** | **0.23** |
| hdr-normal | 0.76 | **0.61** |
| hdr-fast | 0.69 | **0.24** |

DEIO wins **10/11** (ESVIO only on mountain-normal). On the 9 it tracks, ESVIO is close to DEIO;
on robot-fast/mountain-fast ESVIO genuinely fails (DEIO's deep front-end handles the fast motion
that breaks ESVIO's classical init). Full methodology + the collapse caveat:
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
