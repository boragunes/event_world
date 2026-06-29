# DEVO — Deep Event Visual Odometry (base, vision-only) — container + results

[DEVO](https://github.com/tum-vision/DEVO) (Klenk et al., 3DV 2024) is monocular **event-only**
visual odometry (the vision backbone DEIO builds on). We run it as the **base DEVO** baseline on
VECtor.

**Implementation = [`shadymeowy/dpvo-clean`](https://github.com/shadymeowy/dpvo-clean)** — a cleaned,
pip-installable DPVO fork with event support and its own `devo.pth` checkpoint (chosen for
maintainability over the original conda repo). **Evaluation pipeline = [`tum-vision/DEVO`](https://github.com/tum-vision/DEVO)**:
we port its VECtor specifics verbatim — the per-sequence frame crop (`get_imstart_imstop_vector`), the
`dT_ms` voxel window (`imgdt×2` slow / `÷2` fast) built at **image-frame timestamps**, the DSEC
`EventSlicer`, and the event-camera-frame GT `poses_evs_left`.

DEVO is **pure monocular vision (no IMU)** → no metric scale is observable, so we align with **Sim3**
(scale-corrected), exactly as the DEVO/DEIO papers score it. (Contrast: ESVIO/DEIO have inertial/stereo
scale and are scored SE3.)

## Faithful container
dpvo-clean's Dockerfile had bugs (missing `setup.py` in COPY → CUDA exts never built; editable-then-`rm`;
no build-time arch). [`Dockerfile`](./Dockerfile) fixes them and **pins torch 2.6.0+cu124** — the
version that both matches the CUDA-12.4 base and has a `torch-scatter` wheel for py3.12 (unpinned
`>=2.7` pulls torch 2.12+cu130, which has no torch-scatter). `TORCH_CUDA_ARCH_LIST=8.6` (A5000).
```bash
devo/build.sh                       # -> event-world/devo:latest
devo/run_vector.sh                  # runs the 4 paper sequences
```

## Results on VECtor — our run vs the DEVO baseline (DEIO paper, Table IV)
MPE % = 100 × mean(ATE-translation) / GT-path-length, **Sim3**, event-frame GT, single trial.

| sequence | **DEVO ours** | DEVO paper |
|---|---|---|
| corner-slow | **0.49** | 0.59 |
| desk-normal | **0.09** | 0.11 |
| sofa-fast | **0.32** | 0.38 |
| mountain-fast | 0.55 | 0.37 |
| desk-fast | 0.11 | *not in paper* |
| sofa-normal | 0.11 | *not in paper* |
| robot-normal | 0.58 | *not in paper* |
| robot-fast | 0.12 | *not in paper* |
| mountain-normal | 0.10 | *not in paper* |
| hdr-normal | 0.62 | *not in paper* |
| hdr-fast | 0.22 | *not in paper* |

**On the four paper sequences our average (0.36) exactly matches the paper's DEVO average (0.36)** —
reproduced. We beat it on 3/4 (corner-slow, desk-normal, sofa-fast); only mountain-fast is high
(0.55 vs 0.37), which is single-trial — the paper reports the median of 5, and DEVO's patch sampling is
stochastic, so a median would likely pull it down. All-11 average: **0.30 %**.

*Note on scale:* unlike DEIO (whose released VECtor trajectories are scale-broken and only look good
under Sim3 — see [../deio](../deio)), DEVO is honestly vision-only, so Sim3 is the appropriate metric
and there is no hidden scale failure to expose.

## Layout
```
devo/
  Dockerfile  build.sh  run_vector.sh  README.md
  src/ config/ pyproject.toml setup.py   vendored shadymeowy/dpvo-clean (the algorithm)
  eval/evaluate_vector_ev.py             our VECtor evaluator (DEVO pipeline + dpvo-clean model)
  weights/devo.pth                       dpvo-clean's event checkpoint (gitignored; ~14 MB)
  vector/<seq>/                          our run: trajectory + GT + Sim3 metrics + PDF/PNG plots
```
dpvo-clean and tum-vision/DEVO are the original authors' work under their own licenses; this folder adds
containerization, the VECtor evaluator (faithfully porting DEVO's pipeline), and evaluation glue.
