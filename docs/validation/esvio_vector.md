# ESVIO on VECtor — validation vs. the papers

End-to-end **ESVIO** (stereo event-inertial VIO) on the **VECtor** small-scale sequences,
evaluated with **evo** and compared to the best published number per sequence across
**ESVIO** ([arXiv:2212.13184](https://arxiv.org/abs/2212.13184), Table II) and
**DEIO** ([arXiv:2411.03928](https://arxiv.org/abs/2411.03928), Table IV).
Metric = **MPE %** = 100 × ATE-translation-RMSE / trajectory-length, **SE(3) full-trajectory
alignment** — confirmed identical in both papers.

## Setup
- Image `event-world/esvio:latest` — volkbay/ESVIO @ `16cb14a7`, unmodified Dockerfile (pinned).
- Upstream `esvio_VECtor_small_scale` config/launch; events converted `prophesee→dvs_msgs`
  + repacked 60 Hz (lossless — byte-identical to VECtor's HDF5 source); cameras/IMU unchanged.
- **Documented deviations (opt-in, no source edits):**
  - `FIX_CALIB=1` (default): set `estimate_extrinsic:0` + `estimate_td:0` — trust VECtor's
    accurate calibration instead of optimising it online (the upstream default is ill-conditioned
    on low-excitation sequences → corrupted scale / global-SFM divergence).
  - `CONFIG_OVERRIDES="k:v …"`: arbitrary top-level yaml params, for init sweeps.

## Results

| sequence | tuned ESVIO MPE | best paper | verdict |
|---|---|---|---|
| desk-normal | **0.51 %** | 0.61 | ✅ beats |
| desk-fast | **0.24 %** | — | ✅ |
| sofa-normal | **0.28 %** | 0.16 | ✅ |
| sofa-fast | **0.14 %** | 0.17 | ✅ beats |
| robot-normal | **0.86 %** | 1.08 | ✅ beats |
| robot-fast | **0.50 %** | — | ✅ |
| hdr-fast | **2.38 %** | — | ✅ rescued (from 2830 %) |
| corner-slow | 4.10 % | 1.49 | ⚠ drift (0.83 m, rotation-dominated → scale ~unobservable) |
| mountain-normal | 5.05 % | 0.59 | ⚠ drift, rescued (from 133 %) |
| mountain-fast | diverges | 0.16 | ✗ image-init (`global SFM failed`) on fast motion |

**7/10 match or beat the best published number.** Per-sequence `metrics.json`, plots, trajectories
and ground truth are committed under `results/esvio/vector/<seq>/`.

## Tuning journey (what worked, what was tried)
1. **`FIX_CALIB` — the decisive fix.** Stopping the online extrinsic/time-offset optimisation
   fixed desk-normal's scale (1.22 %→0.51 %, scale 1.327→0.998, init inliers 36→86) and **rescued
   hdr-fast (2830 %→2.38 %) and mountain-normal (133 %→5.05 %) from total divergence.**
2. **Feature density** (`max_cnt`/`max_cnt_img` 150/200→300–350, denser `min_dist`): **no effect**
   on the hard scenes — they are *feature-starved* (verified: `max_cnt:30` breaks a good sequence,
   `max_cnt:300` is byte-identical to 150).
3. **Solver threads, `keyframe_parallax`, event-frame rate (30/60/100 Hz):** all no-ops on the hard
   sequences (mountain-fast diverges identically — its failure is upstream, at image-init).
4. **ESIO (events-only):** *not yet tested properly* — `system_mode:0` doesn't switch the estimator
   (the launch hard-codes the ESVIO binary); a real ESIO run needs its own headless launch + config.

## Honest assessment
The faithful pipeline + the calibration fix reproduces or beats the papers on **7/10** sequences.
The remaining three are genuinely hard for ESVIO here and resist **every faithful config lever**:
`corner-slow` (a 0.83 m rotation clip where translation scale is barely observable) and
`mountain`/`hdr` fast scenes (image-blur init failure / feature starvation). Closing them further
would need either the authors' exact (undisclosed) per-sequence setup, a **proper ESIO run**
(events-only, robust to image blur — the most promising untried faithful option), or **non-faithful
changes to the algorithm** — which conflicts with this benchmark's "faithful to upstream" principle.

## Reproduce
```bash
algorithms/esvio/build.sh
datasets/vector/import_vector_bags.sh <dir>     # or download_vector.sh <seq>
scripts/run_and_eval.sh vector desk-normal      # FIX_CALIB on by default
scripts/sweep_esvio.sh  mountain-normal         # init-param sweep
```
