# ESVO2 on VECtor — validation vs. the ESVO2 paper

End-to-end **ESVO2** (direct stereo event VIO — time-surface/AA registration + IMU back-end,
CPU-only; Niu et al., [arXiv:2410.09374](https://arxiv.org/abs/2410.09374)) on the VECtor
small-scale sequences, compared to the paper's Table VI (ATE, cm). **SE(3)** alignment
(stereo+IMU ⇒ metric), exact event-camera-frame GT, single trial, uniform recipe on all sequences.

## Setup — and the input-chunking finding
- Image `event-world/esvo2:latest` — NAIL-HNU/ESVO2 @ `9381fe9d` (pinned; apt Ceres 1.14 = the
  upstream-tested version). Three upstream release defects patched as build plumbing (broken
  message-package CMake, missing `cs_export`, undeclared header dependency) — see
  [esvo2/README](../../esvo2/README.md).
- **Event chunking matters (⚠ undocumented upstream requirement):** ESVO2's TS/AA node samples
  "events received so far" on a 100 Hz clock. With 60 Hz event-array chunks (fine for feature-based
  ESVIO) every tick misses up to ~17 ms of fresh events and desk-normal **diverges 400 m**; repacked
  at **1 kHz** — what upstream's own `events_repacking_tool` produces for their distributed bags —
  the same sequence lands at paper accuracy. Playback at **0.25×** (upstream's own lag remedy;
  sim-time equivalent). Both knobs uniform across all sequences.

## Results — paper sequences (ESVO2 Table VI)

| sequence | **ESVO2 ours (SE3 ATE)** | paper | status |
|---|---|---|---|
| robot-normal | **6.86 cm** | 4.81 | ✅ ≈ paper (1.4×) |
| desk-normal | **20.40 cm** | 16.47 | ✅ ≈ paper (1.2×) |
| hdr-normal | **19.35 cm** | 13.53 | ✅ ≈ paper (1.4×) |
| sofa-normal | ✗ diverged (874 m) † | 40.28 | see † |
| corner-slow | ✗ diverged (10.3 m) ‡ | 2.15 | see ‡ |
| robot-fast | ✗ diverged (252 m) § | 24.18 | ✗ not reproduced |

† *sofa-normal — diverges at any rate:* diverged at the uniform 0.25× (874 m) and diverged harder
at a 0.125× diagnostic (`esvo2/vector-trials/sofa-normal-rate0125`), ruling out compute starvation.
The paper's own 40.28 cm is already ~5× their other normal-sequence numbers — the sequence (highest
event rate of the set) is marginal for the method, and its released form does not reproduce it here.

‡ *corner-slow — end-of-sequence event starvation:* the trajectory is accurate for 38.5 of 39.3 s
(**7.18 cm** diagnostic ATE on that span, same order as the paper's 2.15) and then explodes ~270 m
in the final second, when the near-static ending starves the time surface and the direct optimizer
runs away. A shorter stop-drain does not save it (637 cm; `esvo2/vector-trials/corner-slow-drain2`)
— the runaway is in-sequence. Upstream's interactive workflow (a human stops the system) implicitly
crops this; our headless uniform harness reports the full trajectory, honestly. Committed number =
full trajectory.

§ *robot-fast — the paper's one fast-sequence claim does not reproduce*: full nominal coverage
(97 %) but the estimate diverges to 252 m. Given every other fast sequence also diverges (below),
the paper's 24.18 cm plausibly depended on their exact repacked input and interactive stop timing;
it is not reachable with the released code + native VECtor data under a uniform protocol.

## New coverage — the fast sequences (paper reports only robot-fast)

| sequence | ESVO2 (direct) | SDEVO (deep stereo) | ESVIO (feature E+F+I) | ESIO (feature E+I) |
|---|---|---|---|---|
| desk-fast | ✗ diverged | 46.6 cm | 1.67 % (runs) | ✗ no init |
| sofa-fast | ✗ diverged (840 m) | 29.0 cm | 2.54 % (runs) | ✗ no init |
| hdr-fast | ✗ diverged (165 m) | 22.9 cm | 1.26 % (runs) | ✗ no init |
| mountain-fast | ✗ diverged (711 m) | 165.7 cm | ✗ diverged | ✗ no init |
| robot-fast | ✗ diverged (252 m) § | 27.2 cm | ✗ diverged | ✗ no init |
| mountain-normal | **24.42 cm** ✓ | 8.9 cm | 0.72 % | 1.03 % |

**Finding:** the direct method diverges on every attempted fast sequence in our uniform harness —
consistent with the papers themselves (ESVO2's Table VI attempts only robot-fast on VECtor). The
cross-method picture on fast motion is now three-way: classical-feature ESIO cannot initialise,
classical-direct ESVO2 initialises but diverges, and learned SDEVO completes every sequence.

## Reproduce
```bash
esvo2/build.sh                      # ~10 min, CPU-only
esvo2/run_and_eval.sh desk-normal   # 1 kHz repack (once) + run + SE3 eval
```
Artifacts under [`esvo2/vector/<seq>/`](../../esvo2/vector/); diagnostics under
[`esvo2/vector-trials/`](../../esvo2/vector-trials/).
