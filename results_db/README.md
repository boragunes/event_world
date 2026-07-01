# Event-camera VO/VIO results database

A machine-readable database of **every results table** from a set of event-based
visual(-inertial) odometry papers, so that when we add a new algorithm–dataset
combination we can look up the **best previously reported result** and cite exactly
which paper and table it came from.

Built from the PDFs in [`../papers/`](../papers). **3427 data points** across **74 tables**
from **11 papers / 12 methods**, covering 9 datasets.

## Files

| file | what |
|---|---|
| **`build_db.py`** | single source of truth — every table encoded as a compact matrix; regenerates everything. |
| **`results.csv`** | long form, one row per (paper, table, method, dataset, sequence, metric). The database. |
| **`papers.csv`** | per-paper metadata + colour code. |
| **`leaderboard.md` / `.csv`** | **best reported result** per (dataset, sequence, metric) with provenance. |
| **`discrepancies.csv`** | cells where the *same* method/seq is reported with *different* values across papers (different eval protocols). |
| **`results.tex`** | colour-coded LaTeX `longtable` (one colour per source paper). Compiles standalone. |
| **`conclusions.md`** | the authors' own conclusion(s) for every table (the "asterisks"). |

Regenerate after any edit to `build_db.py`:
```bash
python3 build_db.py
```

## Look up the best result for an algorithm–dataset combo
```bash
python3 build_db.py --best VECtor                 # all sequences/metrics on VECtor
python3 build_db.py --best VECtor desk-normal      # one sequence
python3 build_db.py --best TUM-VIE mocap-desk ATE  # one sequence + metric
```
…or just open `leaderboard.md`. Example row:
```
VECtor  desk_normal  ATE = 1.0 cm -> DPVO (up-to-scale) [DEVO T.2]  (… methods compared)
```

## `results.csv` columns
`paper, paper_short, venue, year, table, method, proposed, modality, metric_type,
alignment, dataset, sequence, sequence_norm, metric, unit, value, status, note`

- **method** — the method that row reports (a paper lists its own method *and* baselines; all captured).
- **proposed** — `yes` if it is that paper's own contribution (authoritative number).
- **modality** — sensor suite: `E`=event, `F`=frame, `I`=IMU, `Stereo …`. e.g. `E+I`, `Stereo E+F+I`.
- **metric_type** — **the "is it metric?" flag**, inferred from modality:
  - `metric` = outputs absolute scale (has IMU and/or stereo).
  - `up-to-scale` = monocular vision-only (DEVO, DPVO, EVO, mono ORB/DSO, RAMP-VO, EDS) — needs Sim3 scale alignment, so a raw ATE/MPE win can be "cheating" on scale.
- **alignment** — how GT was aligned for that table (SE3 / Sim3 / 5 s / metric), as stated by the paper.
- **value / status** — number, or `status` ∈ {`ok`, `failed` (ran but diverged), `n/a` (`-`, not reported)}.
- **metric / unit** — `MPE`(%), `MRE`/`ARE`(deg or deg/m), `ATE`(cm), `RPE_t`(cm/s), `RPE_R`(deg/s), `AUC`(%, higher-better).
- **note** — per-table caveat + the author conclusion (mirrors `conclusions.md`).

### ⚠️ Read `metric_type` and `alignment` before trusting a "best" number
The leaderboard's "best" is the raw lowest error. But:
- A monocular **up-to-scale** method (DPVO/DEVO) aligned with **Sim3** often posts the lowest VECtor
  MPE precisely because scale is corrected for free — not a like-for-like win over a metric method.
- **DEIO** is metric (E+I), yet its released **VECtor/DSEC** trajectories are **scale-broken**: its
  headline MPE relies on scale-correction. Three independent sources confirm this under metric eval
  (Stereo-DEVO T.II: DEIO desk_normal ATE 254.76 cm; SuperEvent T.5: 492.65 cm) and it matches our own
  `event_world` reproduction. See `conclusions.md` (DEIO Table IV) and `discrepancies.csv`.

So: compare **metric vs metric** under **SE3**, and **up-to-scale vs up-to-scale** under **Sim3**.

## Colour code (provenance in `results.tex`)

| paper | short | colour (HTML) | proposed method | sensors |
|---|---|---|---|---|
| 1709.06310 | Ultimate SLAM (RAL'18) | `8B4513` | Ultimate SLAM | mono E+F+I |
| Zhu2017 | EVIO (Zhu, CVPR'17) | `A0522D` | EVIO | mono E+I |
| Hidalgo2022 | EDS (CVPR'22) | `2E8B57` | EDS | mono E+F (up-to-scale) |
| PLEVIO2024 | PL-EVIO (TASE'24) | `1F77B4` | PL-EVIO / PL-EIO | mono E(+F)+I |
| 2212.13184 | ESVIO (RAL'23) | `9467BD` | ESVIO / ESIO | stereo E(+F)+I |
| 2007.15548 | ESVO (TRO'21) | `17BECF` | ESVO | stereo E (metric) |
| 2410.09374 | ESVO2 | `E377C2` | ESVO2 | stereo E+I |
| 2312.09800 | DEVO (3DV'24) | `FF7F0E` | DEVO | mono E (up-to-scale) |
| 2411.03928 | DEIO (ICCV'25) | `D62728` | DEIO | mono E+I |
| 2504.00139 | SuperEvent | `7F7F7F` | OKVIS2+SuperEvent | stereo E+I |
| 2509.08235 | Stereo-DEVO (RAL'25) | `BCBD22` | Stereo-DEVO | stereo E (metric) |

## Datasets & canonical sequence names
Sequence names are normalized (`sequence_norm`) so the same physical sequence collides across papers
(papers spell them differently — `corner-slow`/`corner slow`/`corner_slow`; `Indoor Fly1`/`indoor 1`/
`indoor1 edited` → `indoor_flying1`; see `SEQ_ALIAS` in `build_db.py`).

Datasets: **ECD** (DAVIS240C / Event-Camera-Dataset), **VECtor**, **MVSEC**, **HKU** (stereo arclab),
**Mono-HKU** (arclab `vicon_*`), **UZH-FPV**, **EDS**, **RPG** (Zhou stereo-DAVIS bin/box/desk/monitor),
**TUM-VIE**, **DSEC**. (ECD/EDS also appear as *keypoint-pose* AUC for SuperEvent — a different metric.)

## Extending it
Add a new table by appending one `add(...)` block in `build_db.py` (above the `# @@DATA@@` marker):
```python
add(paper="DEIO", table="IV", dataset="VECtor", metric="MPE", unit="%",
    align="...", note="author conclusion / caveat",
    methods=[("ORB-SLAM3","Stereo F+I",False), ("DEIO","E+I",True), ...],  # (name, modality, is_proposed)
    seqs=["corner_slow", ...],
    values=[[1.49, ...],            # one row per method, aligned to seqs
            [0.50, ...]])           # use "failed" or "-" for non-numeric cells
```
`metric_type` is inferred from `modality`; `python3 build_db.py` re-expands CSV+TeX+leaderboard.

## Provenance
All numbers are transcribed from the papers in `../papers/` (text-extracted; the image-only IEEE tables
in PL-EVIO and ESVO-TRO were read from high-DPI page renders). Cross-checked where the same baseline
appears in multiple papers — surviving discrepancies are catalogued in `discrepancies.csv`.
