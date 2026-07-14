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

## Input repacking — upstream's own tool, and the A/B that mandates it
ESVO2's TS/AA node samples "events received so far" on a fixed clock, making accuracy sensitive to
event-array chunking to a degree documented nowhere upstream (the authors state the 1000 Hz packet
requirement only in issue #4). All repacking is therefore done by **upstream's own
`events_repacking_tool` (`EventMessageEditor`, 1000 Hz)**, built in this image; our tooling only
type-converts (prophesee→dvs, lossless, native chunking; + the issue-#9 2× downscale for the fast
profile) and merges L+R bags byte-preserving to feed the tool. The A/B that settles it, on
desk-normal: 60 Hz chunks → diverges 400 m; our own mechanically-equivalent 1 kHz repacker →
20.40 cm; **upstream's tool → 16.42 cm vs the paper's 16.47** (its gap-lagging array stamps are
functionally part of the system). Playback 0.25× (their lag remedy), uniform.

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
