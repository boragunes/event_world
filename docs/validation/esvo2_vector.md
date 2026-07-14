# ESVO2 on VECtor — validation vs. the ESVO2 paper

End-to-end **ESVO2** (direct stereo event VIO — time-surface/AA registration + IMU back-end,
CPU-only; Niu et al., [arXiv:2410.09374](https://arxiv.org/abs/2410.09374)) on the VECtor
small-scale sequences, compared to the paper's Table VI (ATE, cm). **SE(3)** alignment
(stereo+IMU ⇒ metric), exact event-camera-frame GT, single trial per tier, uniform recipe within
each tier.

## Input preparation — upstream's own repacking tool (and why it matters)
All event repacking is done by **upstream's `events_repacking_tool` (`EventMessageEditor`,
1000 Hz)**, built in our image. Our tooling only does a lossless prophesee→dvs type conversion
(native chunking) and a byte-preserving L+R merge to feed the tool's single input; the tool also
merges the IMU stream. The authors state 1000 Hz event packets are a hard requirement (issue #4) —
it is documented nowhere in the README.

**The repacker A/B** (why the upstream tool is non-negotiable): with a mechanically "equivalent"
1 kHz repacker of our own (same rate, same window-end stamping), desk-normal scored 20.40 cm; with
upstream's tool — whose array stamps *lag* real time after sparse gaps, a quirk the pipeline
evidently expects — desk-normal lands at **16.42 cm vs the paper's 16.47 cm**: reproduction to the
digit. With 60 Hz chunks (fine for feature-based ESVIO) it diverges 400 m. ESVO2's accuracy is
**input-chunking sensitive to a degree undocumented upstream**; only the authors' own tool
reproduces the paper. Playback at 0.25× (their own lag remedy; sim-time equivalent), uniform.

## Results — two configuration tiers, all inputs via upstream's tool

Tier 1 = released code + released configs. Tier 2 = + the authors' fast-sequence recipe from
issue #9 (events downscaled to 320×240, `generation_rate_hz: 200`) plus the one
geometrically-forced dependent parameter (`BM_max_disparity` 300→150 — disparity is in pixels).

| sequence | paper | Tier 1 (released cfg) | Tier 2 (author fast profile) |
|---|---|---|---|
| desk-normal | 16.47 | **16.42 cm** ✅ exact | |
| robot-normal | 4.81 | **6.14 cm** ✅ 1.3× | |
| hdr-normal | 13.53 | **18.67 cm** ✅ 1.4× | |
| mountain-normal | *not in paper* | **35.62 cm** (completes) | |
| sofa-normal | 40.28 | ✗ diverged (143 m) † | |
| corner-slow | 2.15 | ✗ 5.6 m — tail blow-up ‡ | |
| robot-fast | 24.18 | ✗ diverged (30 km) | ✗ diverged (339 m) § |
| desk-fast | *not in paper* | ✗ diverged (201 m) | ✗ diverged (144 m) |
| sofa-fast | *not in paper* | ✗ diverged (683 m) | ✗ diverged (270 m) |
| hdr-fast | *not in paper* | ✗ diverged (147 m) | ✗ diverged (136 m) |
| mountain-fast | *not in paper* | ✗ diverged (48,000 km) | ✗ dead at 0.8 s (2 % coverage) |

† *sofa-normal — not reproducible from the release, now exhaustively*: diverges at 0.25× and
0.125×, and **also with upstream's README step-4 hot-pixel filter applied** (105+101 genuine hot
pixels removed; `esvo2/vector-trials/sofa-normal-hotpixel`). Yet the authors' *released trajectory*
for sofa-normal scores exactly 40.28 under their own protocol — the configuration that produced it
is not in the release (their issue-#11 admission, verbatim below).

‡ *corner-slow — decomposed*: (a) the catastrophic full-trajectory number is an end-of-sequence
event-starvation runaway — and **the authors' own released trajectory stops at 38.3 s, before that
ending**, so it is excluded from their published evaluation too; (b) matched to their exact span,
our runs give a *stable* **6.38 / 7.63 / 7.82 cm across three trials** vs their 2.15 — a systematic
~3× residual, not variance, consistent with the release↔paper parameter gap they acknowledge.

§ *robot-fast*: diverges under the complete union of everything disclosed (released code + their
repacking tool + the issue-#9 fast profile) — and notably, robot-fast is the **only Table VI VECtor
sequence with no released trajectory and no released GT** in their `results/` folder.

## Reconciliation against the authors' released trajectories (`ESVO2/results/`)

The repo ships their 5 VECtor trajectories + the GT they evaluated against. Re-evaluating them
ourselves (evo, SE3): **their trajectories vs their GT reproduce Table VI to the digit**
(2.15 / 16.47 / 4.81 / 40.28 / 13.53) — so their protocol is plain SE3 ATE, their GT ≈ our
event-camera-frame GT (re-evaluating their trajectories against *our* GT shifts results by
< 0.5 cm), and our evaluation pipeline is exactly comparable. The complete decomposition:

| sequence | paper | their traj / our GT | ours, span-matched | verdict |
|---|---|---|---|---|
| desk-normal | 16.47 | 16.94 | **16.42** | reproduced exactly |
| robot-normal | 4.81 | 4.94 | **6.10** | reproduced (1.3×) |
| hdr-normal | 13.53 | 13.41 | **18.67** | reproduced (1.4×) |
| corner-slow | 2.15 | 2.61 | **6.4–7.8** (3 trials) | ~3× residual; tail excluded by *their* span too |
| sofa-normal | 40.28 | 40.26 | ✗ diverges (all disclosed levers) | released config ≠ published run |
| robot-fast | 24.18 | *not released* | ✗ diverges (both tiers) | nothing released to verify against |

## Reading
1. **Reproduced (3/6 paper sequences)**: desk-normal exactly (16.42 vs 16.47);
   robot-normal / hdr-normal within 1.3–1.4× — under a fully faithful input chain.
2. **Explained but not fully reproduced (3/6)**: corner-slow reaches a stable 6.4–7.8 cm on the
   authors' own evaluation span (the tail runaway is outside *their* published span too) — a ~3×
   systematic residual vs 2.15; sofa-normal and robot-fast diverge under every publicly disclosed
   lever (incl. their hot-pixel filter), while their released sofa trajectory scores 40.28 and
   robot-fast ships no trajectory at all. All three are consistent with the authors' issue-#11
   admission that released parameters differ from those behind the published results.
3. **Fast motion**: the direct method diverges on **all five** fast sequences in both tiers. The
   cross-method taxonomy on identical data stands:

| front-end class | representative | VECtor fast sequences |
|---|---|---|
| classical, feature | ESIO | cannot initialise (0/5) |
| classical, direct | ESVO2 | initialises, then diverges (0/5) |
| learned | SDEVO | completes (5/5) |

## Reproduce
```bash
esvo2/build.sh                      # ~10 min, CPU-only (also builds upstream's repacking tool)
esvo2/run_and_eval.sh desk-normal   # upstream 1 kHz repack (cached) + run + SE3 eval
FAST_PROFILE=1 esvo2/run_and_eval.sh robot-fast   # tier 2
```
Artifacts under [`esvo2/vector/`](../../esvo2/vector/) and
[`esvo2/vector-fastprofile/`](../../esvo2/vector-fastprofile/); diagnostics under
[`esvo2/vector-trials/`](../../esvo2/vector-trials/).
