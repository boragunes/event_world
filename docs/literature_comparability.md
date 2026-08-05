# Are the published numbers comparable? — an audit of `results_db/`

Short answer: **no.** Across the plan's six datasets, 34 % of published values are up-to-scale
(Sim(3)-aligned) and 66 % are metric SE(3), and several methods appear in *both* groups depending
on which paper is quoting them. Any table that mixes them without saying so is comparing different
quantities. This is the evidentiary basis for §6.1's Table A / Table B separation, and for the
`sim(3) scale s` column.

Everything below is derived from `results_db/results.csv` (3,775 extracted values, 16 datasets,
69 methods, 11 papers).

## 1. Alignment convention by paper

| paper | convention(s) used | comparable with a stereo/metric method? |
|---|---|---|
| Stereo-DEVO | SE(3) stereo metric | ✅ yes |
| ESVO2 | SE(3) stereo metric | ✅ yes |
| ESVO | SE(3) stereo metric | ✅ yes |
| ESVIO | SE(3) full | ✅ yes |
| Ultimate SLAM | SE(3), 5 s window (3–8 s) | ⚠ partial-window alignment |
| PL-EVIO | SE(3) first 5 s · SE(3) all | ⚠ mixed within one paper |
| DEIO | **seven** different conventions, incl. Sim(3) scale-corrected | ⚠ must be read per table |
| **DEVO** | **Sim(3), median-of-5 — every single row** | ❌ **no** |
| EDS | SE(3) per-paper | ⚠ unclear |
| SuperEvent | SE(3) metric, first 3 rows Sim(3) | ⚠ mixed within one table |

DEVO's paper is the one to watch: **all 750 of its extracted values are Sim(3), median-of-5**.
That includes its quotes of ESVIO, PL-EVIO, ORB-SLAM3 and VINS-Fusion. Those numbers cannot be
placed beside a metric stereo result without a scale caveat.

## 2. The same method, two numbers, because of alignment

This is visible directly in our own Table B for VECtor, where ESVIO carries two published values
per sequence:

| sequence | ESVIO (DEVO paper, Sim(3)) | ESVIO (Stereo-DEVO, SE(3) metric) |
|---|---|---|
| corner-slow | 1.20 | 1.43 |
| robot-normal | 4.30 | 4.95 |
| desk-normal | 5.20 | 6.00 |
| sofa-normal | 4.70 | 5.06 |
| hdr-normal | 1.70 | 1.96 |

The Sim(3) column is uniformly better, by 13–20 %. That is not a measurement difference — it is
the scale correction. Quoting the first number while running the second is exactly the
apples-to-oranges comparison R5 objected to.

## 3. Published values that contradict each other

`results_db/discrepancies.csv` holds **105** method+sequence pairs where two papers publish
different values for the same thing. The worst:

| ratio | dataset | sequence | method | values (source) |
|---|---|---|---|---|
| **52.8×** | DSEC | city04_d | DEIO | 207.6 (DEIO T.IX) vs **10970.03** (Stereo-DEVO T.II) |
| 22.1× | DSEC | city04_c | DEIO | 413.8 (DEIO T.IX) vs 9128.73 (Stereo-DEVO T.II) |
| 13.9× | TUM-VIE | 1d_trans | ESVO | 12.3 (DEIO) vs 0.9 (DEVO) vs 12.54 (ESVO2 / Stereo-DEVO) |
| 9.2× | DSEC | city04_b | ESVIO | 445.8 (DEIO) vs 48.33 (ESVO2) vs 129.7 (Stereo-DEVO) |
| 9.1× | MVSEC | indoor_flying3 | ESVO | 91.0 (DEVO) vs 10.03 (ESVO2 / Stereo-DEVO) |

Most often in conflict: ESVO (23), ESIO (19), ESVIO (18), DEIO (11). By dataset: DSEC (31),
TUM-VIE (19), HKU (14), RPG (13), VECtor (11).

**Stereo-DEVO's quotes of DEIO are the standout.** Their table reports DEIO at 109 m on
`city04_d` where DEIO's own paper reports 2.1 m, and at 254.76 cm on VECtor `desk-normal` where
**our own run measures 3.54 cm**. Two independent sources — DEIO's paper and our reproduction —
agree with each other and disagree with the quote. Since Stereo-DEVO is the primary competitor,
a DUET-VO table that quotes their DEIO column would inherit this.

State it neutrally and let the reader draw the conclusion (§9.3): publish the value, publish our
measurement in Table A, and do not speculate in print about the cause.

## 4. A relabelling to verify before citing

On EDS, DEIO's Table VI and DEVO's Table 4 report **identical values to two decimals** for
ORB-SLAM3 across eight sequences (21.37, 6.15, 27.26, 16.83, 10.12, 32.53, 26.92, 20.57) — but
DEVO states ORB-SLAM3 was run **monocular, up-to-scale**, while DEIO presents the same figures in
a **metric** stereo table. One of the two labels is wrong. Worth checking against both PDFs before
either number is cited.

## 5. What this means for a stereo submission

DUET-VO recovers scale from stereo, so its like-for-like comparison set is the metric group:

| method | modality | metric without external scale? | role |
|---|---|---|---|
| Stereo-DEVO | stereo events | ✅ stereo baseline | Table A — primary competitor |
| ESVO2 | stereo events + IMU | ✅ | Table A (we have it reproduced) |
| ESVIO | stereo events + frames + IMU | ✅ | Table A |
| ESIO | stereo events + IMU | ✅ | Table A |
| DEIO | mono events + IMU | ✅ scale from IMU | Table A |
| ESVO | stereo events | ✅ | Table B |
| ES-PTAM | stereo events | ✅ | Table B |
| DEVO | mono events, no IMU | ❌ **needs Sim(3)** | context only, must be labelled |
| DPVO / ORB-SLAM3 (mono) | mono frames | ❌ | context only |

The plan's Table A/B assignment is already entirely metric-capable, so the scale argument
*strengthens* it. The only care needed is with DEVO and DPVO numbers, which are structurally
up-to-scale and should never sit unlabelled beside a stereo result.

## 6. Why the `s` column settles it

§6.1 notes that the sim(3) scale factor cannot be recovered from a published table cell — only
from a trajectory. So for every Table B method we can state its alignment convention but can
**never verify** whether a given number is genuinely metric or scale-rescued. For every Table A
method we can compute `s` directly and print it.

That asymmetry is the argument for running baselines rather than quoting them, and it is
measurable rather than rhetorical: *quoted numbers are inert; you cannot ask them questions.*

## 7. Action items this audit generates

- [ ] Emit `sim(3) scale s` per run in `scripts/evaluate.py` (currently sim3 is an alignment mode
      but the factor is not reported).
- [ ] Add time-based RPE (cm/s) — the plan's `metrics.py` already implements it; adopt rather than
      re-derive, so both papers share one metric implementation.
- [ ] Tag every Table B cell with its alignment convention in the caption, not just the table note.
- [ ] Verify the EDS ORB-SLAM3 relabelling (§4) against both source PDFs.
- [ ] Re-check Stereo-DEVO's DEIO column against DEIO's paper before citing any of it.
