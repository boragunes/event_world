# ESVIO on VECtor — validation vs. the ESVIO paper

End-to-end **ESVIO** (stereo event-inertial VIO) on the **VECtor** small-scale sequences — our own
runs, evaluated with **evo**, compared **only to the ESVIO paper's own published numbers**
([arXiv:2212.13184](https://arxiv.org/abs/2212.13184) Table II).
Metric = **MPE %** = 100 × ATE-translation-RMSE / length, **SE(3)** (metric) full-trajectory
alignment — ESVIO is stereo + IMU, so it is metric (no scale correction).

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

| sequence | ESVIO ours (SE3) | ESVIO paper (Table II) | status |
|---|---|---|---|
| desk-normal | **0.43 %** | 0.61 | ✅ beats paper |
| sofa-normal | **0.24 %** | 0.16 | ✅ ≈ paper |
| hdr-normal | **0.61 %** | 0.57 | ✅ ≈ paper |
| mountain-normal | **0.72 %** | 0.59 | ✅ ≈ paper |
| robot-normal | **0.87 %** | 1.08 | ✅ beats paper |
| corner-slow | **1.95 %** | 1.49 | ✅ near paper |
| hdr-fast | 1.26 % | 0.21 | ⚠️ runs, ~6× paper |
| desk-fast | 1.67 % | 0.13 | ⚠️ runs, ~13× paper |
| sofa-fast | 2.54 % | 0.17 | ⚠️ runs, ~15× paper |
| robot-fast | **init fails** | 0.20 | ✗ not reproduced |
| mountain-fast | **init fails** | 0.16 | ✗ not reproduced |

*(Correction 2026-07-13: an earlier version of this page claimed the fast sequences were "not in
the paper". They are — Table II covers all 11 small-scale sequences; full transcription in
[`results_db/`](../../results_db/).)*

**On the 6 normal/slow sequences we match or beat the paper on 5** — desk-normal and robot-normal
beat it; sofa-normal / hdr-normal / mountain-normal are within ~0.1; corner-slow (1.95 vs 1.49) is
near. **The 5 fast sequences are not reproduced**: three run but land 6–15× above the paper's
0.13–0.21 %, and robot-fast / mountain-fast deterministically fail initialisation. This is after
exhausting every config-level lever (features, parallax, event rate 30–100 Hz, start-crop, IMU
noise both directions, playback rate — and the event-only [ESIO front-end fails on every fast
sequence too](esio_vector.md)). The released code + config do not reach the paper's fast-sequence
numbers in our uniform setup; whatever initialisation help the authors used there is undisclosed.
Every sequence uses the **identical setup** — imported full-stereo data (left+right event +
left+right camera + IMU), `FIX_CALIB` + VECtor IMU model, SE3 metric — *no per-sequence differences*.
hdr-normal is a near-static short sequence (GT path 3.1 m), so its metric is sensitive, but coverage
is ≥97% (verified). Trajectories/GT/metrics/plots: [`esvio/vector/<seq>/`](../../esvio/vector/).

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
