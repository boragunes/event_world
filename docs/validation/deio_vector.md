# DEIO on VECtor — published trajectories vs our ESVIO run

[DEIO](https://arxiv.org/abs/2411.03928) (deep monocular event–inertial odometry, ICCV 2025)
tops VECtor Table IV. This report compares DEIO to our ESVIO run on the same 11 small-scale
sequences, with the same evo pipeline and the same VECtor ground truth.

## Provenance & method (read this first)
- DEIO's public repo has **no VECtor eval script or config** (only `davis240c.py` / `uzh-fpv.py`
  run out of the box). It **does** release the authors' VECtor **trajectories**
  (`estimated_trajectories/VECtor/`). We evaluate *those* — we did **not** re-run DEIO on VECtor.
- **Alignment:** DEIO is evaluated with **Sim3 (scale-corrected)** — this is DEIO's own
  convention (`correct_scale=True` in their eval notebook), standard for the DPVO/DEVO family.
  Our **ESVIO** numbers use **SE3 (metric)**, ESVIO's convention. So the two columns are each
  faithful to their own paper but *not* aligned the same way (Sim3 ≤ SE3 always).
- Metric: MPE % = 100 × ATE-RMSE / trajectory-length. Same GT, same evo code.
- Verified: DEIO trajectories share VECtor's absolute timestamps (µs); under SE3 four of them
  showed a constant scale error that vanishes under Sim3 (e.g. desk-normal 29.7%→0.34%),
  confirming they are scale-ambiguous outputs meant for Sim3 evaluation.

## Results — MPE %
| sequence | ESVIO (SE3, our run) | DEIO (Sim3, published) | better |
|---|---|---|---|
| desk-normal | 0.43 | **0.34** | DEIO |
| desk-fast | 0.24 | **0.15** | DEIO |
| sofa-normal | 0.24 | **0.19** | DEIO |
| sofa-fast | 2.54 | **0.50** | DEIO |
| robot-normal | 0.87 | **0.38** | DEIO |
| robot-fast | *init fails* | **0.17** | DEIO |
| corner-slow | 1.95 | **1.02** | DEIO |
| mountain-normal | **0.72** | 1.36 | ESVIO |
| mountain-fast | *init fails* | **0.26** | DEIO |
| hdr-normal | 3.62 | **0.71** | DEIO |
| hdr-fast | 1.26 | **0.30** | DEIO |

**DEIO wins 10/11.** Most striking: DEIO cleanly handles **robot-fast** and **mountain-fast**,
the exact sequences where ESVIO's classical global-SFM init diverges — the deep front-end is
robust to the fast motion that breaks feature-based initialization. ESVIO's only win is
mountain-normal. (Part of DEIO's margin is the scale-corrected alignment; the qualitative story
— deep method robust on fast/HDR motion — holds regardless.)

## Reproducing DEIO ourselves
The faithful container ([`deio/`](../../deio/)) builds DEIO from its `environment.yml` + GTSAM.
Because VECtor isn't runnable upstream, our *own* DEIO run is validated on **UZH-FPV**
(event–inertial, the README's example) under `deio/uzhfpv/` — pending the `DEVO.pth` weights and
the UZH-FPV data.
