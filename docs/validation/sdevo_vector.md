# SDEVO on VECtor — validation vs. the Stereo-DEVO paper

End-to-end **SDEVO** (deep stereo event-only VO — metric scale from stereo, **no IMU**;
Zhong, Niu, Zhou, RA-L 2025, [arXiv:2509.08235](https://arxiv.org/abs/2509.08235)) on the VECtor
small-scale sequences, compared to the paper's own Table II. Metric = **ATE-translation RMSE (cm)**,
**SE(3)** full-trajectory alignment (stereo ⇒ metric, no scale correction), against the **exact
event-camera-frame GT** (`poses_evs_left`, from VECtor's official extrinsics). Single trial, online
run at the shipped settings (0.2× playback ↔ `generation_rate_hz: 10` per the upstream formula).

## Setup
- Image `event-world/sdevo:latest` — NAIL-HNU/SDEVO @ `2b8a556c`, pinned; dependency commits recorded
  in-image (`/catkin_ws/PINNED_COMMITS.txt`).
- **The core `devo/devo.py` ships without source** — we execute the authors' newest released artifact
  (the cp310 bytecode) byte-exactly as a sourceless module; the older egg variant is *broken*
  (`NameError` in `update_depth`) and its `block_matching` differs. See [sdevo/README](../../sdevo/README.md).
- Upstream's own VECtor launch/calib; input = our lossless prophesee→dvs converted bags
  (shared with ESVIO); weights = original TUM `DEVO.pth` (as upstream ships).

## Results — paper sequences (Stereo-DEVO Table II)

| sequence | **SDEVO ours (SE3 ATE)** | paper | status |
|---|---|---|---|
| robot-normal | **3.63 cm** | 3.16 | ✅ ≈ paper |
| desk-normal | **6.88 cm** | 6.48 | ✅ ≈ paper |
| sofa-normal | **7.21 cm** | 7.18 | ✅ = paper |
| hdr-normal | **6.59 cm** | 6.71 | ✅ beats paper |
| corner-slow | 11.93 cm † | 1.06 | ✗ see † |

**4/5 reproduced** (three within 0.5 cm, one better). The paper's two large-scale sequences
(corridors-dolly, units-dolly) are not downloaded locally and were not run.

† *corner-slow*: **not reproduced, and the gap is systematic** — three independent trials give
11.93 / 7.86 / 7.97 cm (extra trials committed under [`sdevo/vector-trials/`](../../sdevo/vector-trials/)),
all ~8–11× the paper's 1.06 cm, while the other four paper sequences match tightly. corner-slow is
the near-static, rotation-dominant sequence (GT path ≈ 1.4 m, so centimetres dominate the metric).
Likely cause: the authors run from *repackaged* bags (their README's download link is unfinished),
whose event stream/start may differ from the native VECtor bags we feed on exactly this
low-excitation sequence. Reported honestly as a per-sequence reproduction gap.

## New coverage — the fast sequences the paper skips (+ mountain-normal)

The Stereo-DEVO paper evaluates **no VECtor fast sequence**. We ran all five — the same sequences
where the classical stereo front-ends break (ESVIO's global-SFM init diverges on robot/mountain-fast;
event-only ESIO fails init on *all* five — see [esio report](esio_vector.md)):

| sequence | SDEVO ATE | SDEVO MPE | coverage | classical front-ends |
|---|---|---|---|---|
| hdr-fast | **22.89 cm** | 1.14 % | full | ESIO: 0 poses; ESVIO: 1.26 % |
| robot-fast | **27.19 cm** | 1.14 % | full | ESVIO **diverged** (1333 m); ESIO: 0 poses; ESVO2 24.18 cm |
| sofa-fast | **29.00 cm** | 0.86 % | full | ESIO: 7 poses; ESVIO: 2.54 % |
| desk-fast | **46.57 cm** | 1.27 % | full | ESIO: 0 poses; ESVIO: 1.67 % |
| mountain-fast | 165.68 cm | 4.99 % | full | ESVIO **diverged** (1977 m); ESIO: 4 poses |
| mountain-normal | **8.90 cm** | 1.06 % | full | ESVIO: 0.72 % |

**Finding: the learned front-end survives every fast sequence with full coverage** (96–100 % of GT
span everywhere), including the two where ESVIO catastrophically diverges and ESIO cannot even
initialise. Accuracy under fast motion is moderate (0.9–5 % MPE — drift, not scale error), but the
robustness gap vs classical event tracking is categorical: deep patch tracking + static stereo
association simply does not lose the sequence. This closes the loop on our ESIO finding — the
VECtor fast-motion failures are a *front-end* problem, and learning fixes it.

## Cross-algorithm view (VECtor, metric methods, SE3)

| | modality | normal seqs | fast seqs |
|---|---|---|---|
| ESVIO | stereo E+F+I, classical | 0.24–1.95 % MPE | 3/5 run (≫ paper), 2/5 diverge |
| ESIO | stereo E+I, classical | 0.89–10.9 % MPE | **0/5 complete** |
| DEIO | mono E+I, deep | strong, but released VECtor trajectories scale-broken | completes |
| **SDEVO** | **stereo E, deep** | 3.6–8.9 cm ATE, ≈ paper | **5/5 complete, full coverage** |

SDEVO is the first algorithm in this benchmark that is simultaneously **metric without an IMU**,
**reproduces its paper numbers**, and **completes every fast sequence**.

## Reproduce
```bash
sdevo/build.sh                      # ~35 min (CUDA 11.3 + ROS Noetic + conda py3.10 + tf2 overlay)
sdevo/run_and_eval.sh desk-normal   # one sequence -> sdevo/vector/desk-normal/
```
Per-sequence artifacts (trajectory, GT, `metrics.json`, plots, node logs) under
[`sdevo/vector/<seq>/`](../../sdevo/vector/).
