# DEIO on VECtor — our run vs the DEIO paper (Table IV)

[DEIO](https://arxiv.org/abs/2411.03928) (deep **monocular event–inertial** odometry, ICCV 2025).
We run DEIO ourselves in the faithful `event-world/deio` container, produce **our own trajectories**,
and score them with **SE3 (metric) alignment** — DEIO fuses an IMU, so its scale is supposed to be
observable, and the metric must therefore be metric.

## Results — MPE % (SE3, metric-honest)
MPE = 100 × mean(ATE-translation) / GT-path-length (the authors' MPE formula), **SE3** alignment,
ground truth in the **event-camera frame** (see *GT frame* below).

| sequence | **DEIO ours (SE3)** | authors' released (SE3) | paper reports (Sim3) |
|---|---|---|---|
| corner-slow | **1.89** | 4.40 | 0.50 \* |
| desk-normal | **0.33** | 23.69 | 0.13 \* |
| sofa-fast | **0.14** | 0.48 | 0.44 \* |
| mountain-fast | **0.52** | 0.26 | 0.24 \* |
| desk-fast | 0.11 | — | *not in paper* |
| sofa-normal | 0.29 | — | *not in paper* |
| robot-normal | 0.54 | — | *not in paper* |
| robot-fast | 0.25 | — | *not in paper* |
| mountain-normal | 1.70 | — | *not in paper* |
| hdr-normal | 10.39 † | — | *not in paper* |
| hdr-fast | 0.66 | — | *not in paper* |

**Average (excl. hdr-normal): 0.64 %.** On the four paper sequences, under the **same SE3 metric**,
our reconstruction is **more accurate than the authors' own released trajectories on 3 of 4**
(corner-slow 1.89 vs 4.40, desk-normal 0.33 vs 23.69, sofa-fast 0.14 vs 0.48; only mountain-fast loses,
0.52 vs 0.26).

## \* Why the paper's numbers are misleading
**The DEIO paper evaluates with `correct_scale=True` (Sim3 / scale-correction).** For a *monocular*
method, metric scale is unobservable on low-excitation sequences — and DEIO's released trajectories
are in fact **scale-broken there**. Turning scale-correction off (i.e. honest SE3) on the **authors'
own released `estimated_trajectories/VECtor/` files**:

| | Sim3 (what they publish) | SE3 (honest) |
|---|---|---|
| corner-slow (released) | 0.57 | **4.40** |
| desk-normal (released) | 0.28 | **23.69** |
| sofa-fast (released) | 0.44 | 0.48 |
| mountain-fast (released) | 0.26 | 0.26 |

So Table IV's headline numbers (0.50, 0.13) are **scale-correction artifacts** on the low-motion
sequences, not metric accuracy — the underlying trajectories drift by 4–24 % once you stop letting
the evaluator rescale them. The fast sequences (Sim3≈SE3) are genuinely metric. *(We verified the
released files reproduce Table IV exactly under the authors' own `evo_evaluation_vector.ipynb`, so
they are the real DEIO runs, not the DEVO baseline.)*

**Our trajectories, by contrast, are metric** — Sim3≈SE3 on every excited sequence (corner-slow
1.85/1.89, desk-normal 0.30/0.33, sofa-fast 0.14/0.14), i.e. our IMU actually recovers scale.

## GT frame
DEIO estimates the **event-left camera** pose; the authors score against `poses_evs_left.txt`
(GT in that frame). We transform VECtor's body-frame GT into the event-camera frame via the
event↔IMU extrinsic (`<seq>_gt.txt` here) before evaluating — otherwise a lever-arm inflates the
rotation-heavy sequences (corner-slow was 2.63 against the body-frame GT, 1.89 corrected). *(Our
extrinsic is from the ESVIO VECtor calibration, not the authors' exact one, so the released numbers
above land at 0.57/4.40 rather than precisely 0.50/4.x — the Sim3-vs-SE3 conclusion is unaffected.)*

## † hdr-normal — genuine scale failure, honestly reported
hdr-normal is near-static (GT path ≈ 3 m), so **monocular scale is unobservable** for *anyone* — our
run is scale-broken here too (SE3 10.39 vs Sim3 0.97), exactly as DEIO's are on corner-slow/desk-normal.
SE3 reports it honestly; Sim3 would hide it. (Stereo ESVIO recovers metric scale on this sequence:
0.61 % SE3.)

## Provenance
`deio/vector/<seq>/` = **our** DEIO run (`stamped_traj.tum`), SE3, event-frame GT (`<seq>_gt.txt`),
`metrics.json` (both mean- and RMSE-based MPE), and plots. We never report the authors' trajectories
as our result — they appear here only as the *reference* whose scale-correction dependence we expose.
The earlier "2–5× gap to the paper" was an artifact of (a) the body-frame GT and (b) comparing our
honest SE3 to their scale-corrected Sim3; corrected for both, our metric-faithful numbers are competitive
with — and on most paper sequences better than — DEIO's own released runs.
