# ESVO2 — direct stereo event VIO — container + results

[ESVO2](https://github.com/NAIL-HNU/ESVO2) (Niu, Zhong, Lu, Shen, Gallego, Zhou;
[arXiv:2410.09374](https://arxiv.org/abs/2410.09374)) is **direct** stereo event odometry with an
IMU back-end: time-surface/AA registration (no features, no learning), Ceres, **CPU-only**. In our
matrix it is the *direct classical* counterpart to ESVIO/ESIO (feature-based classical) and
SDEVO/DEVO/DEIO (learned).

## Provenance & faithfulness
| | |
|---|---|
| Upstream | https://github.com/NAIL-HNU/ESVO2 @ `9381fe9d` (pinned) |
| Base image | `ros:noetic-perception` + apt Ceres **1.14** (exactly the upstream-tested version) |
| Deps | upstream `dependencies.yaml` set (ethz-asl shims, minkindr C++ only); commits recorded in-image |

**Upstream build fixes (build plumbing only — no algorithm code):** in a clean workspace the release
does not compile: `events_repacking_tool` calls `add_message_files()` before any catkin
`find_package` loads the genmsg macros and never calls `cs_export()`, while `esvo2_core` #includes
its generated `V_ba_bg.h` header without declaring the dependency. The Dockerfile patches exactly
that (a `find_package` line, a `cs_export()` line, a `<depend>` line).

## The input-chunking finding (why 1 kHz repacking is required)
ESVO2's `image_representation` node samples "all events received so far" on a **100 Hz** clock
(`generation_rate_hz: 100`). With our 60 Hz-chunked dvs bags (fine for feature-based ESVIO), every
TS tick is missing up to ~17 ms of the freshest events — fatal for a 20 ms-decay surface:
desk-normal **diverged 400 m**. Repacked at **1 kHz** (exactly what upstream's own
`events_repacking_tool` produces for their distributed bags), the same sequence lands at paper
accuracy. The 16× message count also raises CPU load, so playback runs at **0.25×**
(upstream's README itself prescribes reducing the rate on lag; `use_sim_time` makes this
result-equivalent). Both knobs are upstream's own remedies; conversion is lossless (event counts
conserved) and cached as `data/vector/<seq>/*_dvs1k.bag`.

## Run on VECtor
```bash
esvo2/build.sh                      # ~10 min, CPU-only
esvo2/run_and_eval.sh desk-normal   # repack (once) + run + SE3 eval -> esvo2/vector/desk-normal/
```
Headless launch = upstream `system_vector.launch` minus rviz/rqt, with the trajectory path
redirected to the mounted output (upstream hardcodes a home directory). Evaluation: **SE(3)**
(stereo+IMU ⇒ metric), against the exact event-camera-frame GT (`poses_evs_left`). Results land in
`esvo2/vector/<seq>/` (trajectory + GT + `metrics.json` + plots + node log); see
[docs/validation/esvo2_vector.md](../docs/validation/esvo2_vector.md) for the comparison to the
paper's Table VI.
