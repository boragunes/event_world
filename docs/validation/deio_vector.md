# DEIO vs ESVIO on VECtor — under DEIO's own evaluation logic

[DEIO](https://arxiv.org/abs/2411.03928) (deep monocular event–inertial odometry, ICCV 2025)
tops VECtor Table IV. This compares DEIO to our ESVIO run on the same 11 small-scale sequences,
**both evaluated with DEIO's exact published logic** so it is apples-to-apples.

## Provenance & method
- DEIO's public repo has **no VECtor eval script/config** (only `davis240c.py`/`uzh-fpv.py` run
  out of the box). It releases the authors' VECtor **trajectories** (`estimated_trajectories/VECtor/`).
  We evaluate *those* — we did not re-run DEIO on VECtor. ESVIO results are **our own run**.
- **DEIO's exact metric** (from `utils/eval_utils.py`), applied to *both* methods via
  [`scripts/compare_deio_logic.py`](../../scripts/compare_deio_logic.py):
  - **Sim3** alignment (`align=True, correct_scale=True`)
  - **MPE = mean(APE_translation) / GT_path_length × 100** — the **mean**, not RMSE
  - association `max_diff = 1 s`
- **Collapse guard (ours).** Sim3 hides scale error — and can mask a *diverged* estimate by
  shrinking it to a point near the GT centroid, where `mean/length` still looks small (the path is
  long). After alignment we compare the estimate's spatial extent to the GT's; **< 0.5× ⇒ FAIL**
  (a collapsed estimate, not a track), instead of reporting the artifact number.

## Results — MPE % (DEIO's logic, lower is better)
| sequence | ESVIO (our run) | DEIO (published) | winner |
|---|---|---|---|
| desk-normal | 0.38 | **0.30** | DEIO |
| desk-fast | 0.22 | **0.14** | DEIO |
| sofa-normal | 0.22 | **0.16** | DEIO |
| sofa-fast | 0.87 | **0.46** | DEIO |
| robot-normal | 0.39 | **0.34** | DEIO |
| robot-fast | **FAIL** | **0.15** | DEIO |
| corner-slow | 1.56 | **0.83** | DEIO |
| mountain-normal | **0.52** | 0.76 | ESVIO |
| mountain-fast | **FAIL** | **0.23** | DEIO |
| hdr-normal | 0.76 | **0.61** | DEIO |
| hdr-fast | 0.69 | **0.24** | DEIO |

**DEIO wins 10/11; ESVIO wins mountain-normal.**

## Two findings
1. **Fair fight helps ESVIO — where it tracks.** Re-scoring ESVIO with DEIO's logic (Sim3 removes
   benign scale error; mean < RMSE) drops its numbers vs. its own SE3 report
   ([esvio_vector.md](esvio_vector.md)): sofa-fast 2.54→0.87, hdr-normal 3.62→0.76, desk-normal
   0.43→0.38. On the 9 sequences ESVIO genuinely tracks it is close to DEIO (0.22–1.56 vs 0.14–0.83).
2. **The metric would have masked ESVIO's real failures.** On robot-fast and mountain-fast ESVIO's
   estimate **collapses** (Sim3 scale ≈ 1e-4, spatial extent ~0.1× GT). Raw DEIO-logic MPE reports a
   bogus 1.29% / 0.89%; the collapse guard correctly calls them **FAIL**. DEIO, the deep method,
   tracks both (0.15% / 0.23%) — its learned front-end is robust to the fast motion that breaks
   ESVIO's classical init. The fast-sequence failures are real under either alignment.

## Reproduce
```bash
python scripts/compare_deio_logic.py vector esvio deio
```
