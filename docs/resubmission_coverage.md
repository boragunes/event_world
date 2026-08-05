# DUET-VO → RA-L: benchmark coverage status

Generated against `RESUBMISSION_PLAN.pdf` (§3.4 inventory, §6.1 Table A/B discipline) and the
actual state of this repository. **Table A** = cells we run ourselves, full protocol disclosed.
**Table B** = literature, cited. Reason codes per §6.1: `div` ran/diverged · `nc` no public code ·
`ng` no ground truth · `oom` resource limit · `ns` sensor modality absent.

## 1. Headline

| | count | note |
|---|---|---|
| Plan inventory | **47** | 34 S-DEVO sequences + 13 M3ED |
| Sequences we have run ourselves | **5** | VECtor small-scale, every one at 6 algorithms deep |
| Sequences staged but not in the plan | **6** | VECtor fast + mountain-normal — bonus evidence |
| Sequences with literature numbers ready | **34** | all of S-DEVO's set, already in `results_db/` |
| Sequences with no data and no numbers | **13** | M3ED — S-DEVO published none, every cell must be self-run |

Table A target is 47 sequences × 5 methods (DUET-VO, S-DEVO, DEIO, ESIO, ESVIO) = **235 cells**;
**20 are done** (5 sequences × 4 baselines). That percentage understates progress badly: the
per-baseline cost is containerising and validating the algorithm, which is one-time and **already
paid for four of the five methods**. What remains is mostly staging data and running.

## 2. The 34 S-DEVO sequences

Legend: ✅ run by us · ⬜ not run · **stage** = raw data present on this box.

| dataset | sequences | stage | DUET-VO | S-DEVO | DEIO | ESIO | ESVIO | lit. (Table B) |
|---|---|---|---|---|---|---|---|---|
| **VECtor** small-scale | robot_normal, corner_slow, hdr_normal, sofa_normal, desk_normal | ✅ 5/5 | ⬜ | **✅ 5** | **✅ 5** | **✅ 5** | **✅ 5** | ✅ |
| **VECtor** large-scale | corridors_dolly, units_dolly | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ✅ |
| **rpg** | box, monitor, bin, desk, reader | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ✅ |
| **MVSEC** | indoor 1–4 (edited) | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ✅ |
| **DSEC** | city04 a–d, city09 a–e, city11 a–b | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ✅ |
| **TUM-VIE** | 1d/3d/6d_trans, desk, desk2 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ✅ |
| **Other** | hnu_campus, drone_fast | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ✅ |
| **M3ED** | 13 sequences | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ✗ none published |

**The one block that is complete is the one the review attacked.** §3.4 records that the IROS
submission used `corridors_dolly` + `units_dolly` and dropped all five VECtor small-scale
sequences — R5's "over-representation of large-scale sequences". Those five are exactly the
sequences already run here, at author defaults, with committed trajectories and per-sequence
provenance.

## 3. Bonus coverage — beyond the S-DEVO inventory

Six further VECtor sequences are staged and run at 6 algorithms: `robot-fast`, `desk-fast`,
`sofa-fast`, `hdr-fast`, `mountain-fast`, `mountain-normal`. They are in VECtor's own release and
in ESVIO's Table II, but S-DEVO never evaluated them. They produce a result no one has published:

| front-end class | representative | VECtor fast sequences |
|---|---|---|
| classical, feature-based | ESIO | cannot initialise — 0/5 |
| classical, direct | ESVO2 | initialises, then diverges — 0/5 |
| learned | S-DEVO | completes all — 5/5 |

## 4. Methods: build status (the expensive, one-time part)

| method | container | validated against its own paper | Table A ready |
|---|---|---|---|
| S-DEVO | ✅ `sdevo/` | 4/5 paper sequences reproduced | ✅ |
| DEIO | ✅ `deio/` | ≥ their released trajectories on 3/4 under SE3 | ✅ |
| ESVIO | ✅ `esvio/` | 5 of 6 slow/normal match or beat paper | ✅ |
| ESIO | ✅ `esvio/` (variant) | new coverage; paper has no VECtor table | ✅ |
| ESVO2 | ✅ `esvo2/` | desk-normal exact (16.42 vs 16.47); 3 seqs diverge, documented | **promotable B→A** |
| DEVO | ✅ `devo/` | 4-seq average 0.36 = paper's 0.36 | ✅ (extra) |
| **DUET-VO** | ✗ not on this machine | — | **blocked** |

ESVO2 is listed in the plan as Table B (literature). We have it reproduced with full provenance —
inputs through the authors' own repacking tool, their released trajectories re-scored to their
Table VI exactly — and its failures carry real `div` reason codes rather than bare dashes. It can
move to Table A if you want it.

## 5. Metric gaps vs §6.1

Our evaluator (`scripts/evaluate.py`) currently emits ATE and distance-based relative error.
The plan's table format needs three more things:

| required | have | gap |
|---|---|---|
| ATE (cm) | ✅ | — |
| RPE (cm/s) | ⚠ per-metre, not per-second | plan's `metrics.py` implements wall-clock RPE because evo cannot |
| sim(3) scale `s` | ⚠ sim3 supported as alignment, value not emitted | one-line change; §6.1 calls this column the quiet weapon |
| median [min, max] over N runs | ⚠ single-trial except where deliberately repeated | needs an N-run driver |
| reason codes | ⚠ `status.json` has ok/diverged/failed | map onto div/nc/ng/oom/ns |

## 6. Blockers

1. **Disk.** §M1.3 budgets against 337 GB free; actual free space is **36 GB**. `data/vector` is
   191 GB and Docker images 116 GB. Roughly 110 GB is regenerable cache. DSEC will not fit until
   this is resolved.
2. **Four datasets unstaged**, with download tooling for VECtor only (`datasets/vector/`).
3. **DSEC ground truth** (§M1.4): no released GT trajectories; both sides derive from LIO-SAM, and
   two LIO-SAM runs are two different ground truths. Author request should land before DSEC runs.
4. **DUET-VO and the AGX Orin** are not on this machine — M2.1 and all of Phase 3 are out of scope
   here as things stand.
