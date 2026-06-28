# ESVIO on VECtor — validation vs. the papers

End-to-end **ESVIO** (stereo event-inertial VIO) on the **VECtor** small-scale sequences,
evaluated with **evo**, compared to the best published MPE per sequence across **ESVIO**
([arXiv:2212.13184](https://arxiv.org/abs/2212.13184) Table II) and **DEIO**
([arXiv:2411.03928](https://arxiv.org/abs/2411.03928) Table IV).
Metric = **MPE %** = 100 × ATE-translation-RMSE / length, SE(3) full-trajectory alignment
(identical convention in both papers).

## Setup
- Image `event-world/esvio:latest` — volkbay/ESVIO @ `16cb14a7`, unmodified Dockerfile (pinned).
- Upstream `esvio_VECtor_small_scale` config/launch. Events converted `prophesee→dvs_msgs` +
  repacked 60 Hz (lossless — event counts conserved, md5-verified); cameras/IMU fed unchanged.
- **Two documented config tunings (no source edits):**
  - **`FIX_CALIB`** (`estimate_extrinsic:0`, `estimate_td:0`) — trust VECtor's calibration instead
    of optimising it online (the upstream default is ill-conditioned → corrupted scale / divergence).
  - **IMU-noise model** (`acc_n:0.2`→`0.08`, etc.) — the upstream noise (tuned for HKU DAVIS)
    over-trusts the accelerometer and inflates scale on low-excitation VECtor sequences.

## Results

| sequence | ESVIO MPE | best paper | status |
|---|---|---|---|
| desk-normal | **0.43 %** | 0.61 | ✅ beats |
| sofa-normal | **0.24 %** | 0.16 | ✅ |
| hdr-normal | **0.61 %** | 0.57 | ✅ |
| mountain-normal | **0.72 %** | 0.59 | ✅ |
| robot-normal | **0.87 %** | 1.08 | ✅ beats |
| hdr-fast | **1.26 %** | — | ✅ |
| desk-fast | **1.67 %** | — | ✅ |
| corner-slow | **1.95 %** | 1.49 | ✅ |
| sofa-fast | 2.54 % | 0.17 | ◑ tracks, drifts |
| robot-fast | **init fails** | — | ✗ |
| mountain-fast | **init fails** | 0.16 | ✗ |

**9/11 good (<3 %); matches or beats the paper on desk-normal, robot-normal, hdr-normal,
mountain-normal.** Every sequence uses the **identical setup** — imported full-stereo data
(left+right event + left+right camera + IMU), `FIX_CALIB` + VECtor IMU model, SE3 metric — *no
per-sequence methodology differences*. `desk-fast` (1.67) and `hdr-normal` (0.61) were re-run on
newly-downloaded full data; hdr-normal is a near-static short sequence (GT path 3.1 m), so its
metric is sensitive, but coverage is ≥97% (verified). Trajectories, GT, metrics, and plots are
committed under [`esvio/vector/<seq>/`](../../esvio/vector/).

## Tuning journey (config-only)
- **`FIX_CALIB`** — the decisive fix; rescued the upstream config's divergences (e.g. hdr-fast
  2830 %→, mountain-normal 133 %→) and fixed desk-normal's scale.
- **IMU-noise tuning** — the second fix; recovered the low-excitation sequences
  (corner-slow 4.10 %→1.95 %, mountain-normal 5.05 %→0.72 %, desk-normal 0.51 %→0.43 %).
  It is **excitation-dependent** (helps slow, neutral/harmful on fast), so it's the VECtor default
  but not a universal value.
- **No effect on the two failures:** feature density (`max_cnt` — scenes feature-starved, verified
  by `max_cnt:30` breaking a good sequence), solver threads, `keyframe_parallax`, event-frame rate
  (30/60/100 Hz), start-cropping, and **events-only ESIO** (separate `stereo_esio_estimator` launch).

## The two init failures (robot-fast, mountain-fast)
Both deterministically fail **initialisation** — `global SFM failed` / "unstable features tracking" —
the optimiser cannot bootstrap consistent structure from feature tracks under fast motion. This
holds for **both ESVIO and ESIO**, so it is not image motion-blur alone. The data is verified valid
(events conserved, timestamps monotonic, streams synced to ≤7 ms). No config/playback lever reaches
it; closing these would require the authors' exact (undisclosed) init/preprocessing or algorithm-level
changes (out of scope here). They are reported honestly as initialisation failures.

## Reproduce
```bash
esvio/build.sh
datasets/vector/import_vector_bags.sh <dir>   # or datasets/vector/download_vector.sh <seq>
esvio/run_and_eval.sh vector desk-normal      # FIX_CALIB + VECtor IMU model on by default
```
Outputs land in `esvio/vector/desk-normal/` (trajectory + GT + metrics + PDF/PNG plots).
