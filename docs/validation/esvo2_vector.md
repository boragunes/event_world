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

† *sofa-normal*: diverges at the uniform 0.25× and at a 0.125× diagnostic
(`esvo2/vector-trials/`) — not compute-bound. The paper's own 40.28 cm is already ~5× their other
normal-sequence numbers; the sequence (highest event rate of the set) is marginal for the method
and its released form does not reproduce it.

‡ *corner-slow — end-of-sequence event starvation*: centimetre-accurate for 38.4 of 38.8 s
(**7.69 cm** diagnostic ATE on that span, same order as the paper's 2.15), then the near-static
ending starves the time surface and the direct optimizer runs away in the final fraction of a
second. A shorter stop-drain does not prevent it — the runaway is in-sequence. Upstream's
interactive workflow (a human stops the system) implicitly crops this; our headless uniform
harness reports the full trajectory. Committed number = full trajectory.

§ *robot-fast — the paper's one fast-sequence claim does not reproduce* under the complete union
of everything the authors have publicly disclosed: released code + their own repacking tool + the
issue-#9 fast profile. The authors' own words on the release↔paper relationship (issue #11, on
TUM-VIE reproduction): *"it is likely that the parameters in the released version differ slightly
from those we used to generate the published results."* Issue #6 further discloses that their
MVSEC numbers were computed on a *segment* of the sequence.

## Reading
1. **Reproduced (3/6 paper sequences)**: desk-normal exactly (16.42 vs 16.47);
   robot-normal / hdr-normal within 1.3–1.4× — under a fully faithful input chain.
2. **Not reproduced (3/6)**: corner-slow (end-starvation runaway; accurate until the final
   instant), sofa-normal (diverges at any rate), robot-fast (diverges under every disclosed
   configuration). Consistent with the authors' issue-#11 admission.
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
