# Reusable prompt — add `{ALGORITHM} × {DATASET}` to the event-SLAM benchmark

Paste everything below the line into a **fresh Claude Code chat** opened in `/home/ogam/event_world`.
Edit only the **FILL THESE IN** block; leave the rest unchanged. It reproduces the same
structure, rigor, and gotcha-handling used for ESVIO × VECtor.

---

You are extending a reproducible **event-camera SLAM benchmark** at `/home/ogam/event_world`
(already a git repo). Mission: run one algorithm on one dataset in a way that is **faithful to
the algorithm's upstream repo**, fed with **minimal, lossless preprocessing**, evaluated with
**evo**, and **validated against the numbers published in the relevant paper(s)** — publishing
the Dockerfile, run scripts, estimated trajectories, ground truth, metrics and plots.

### ▼ FILL THESE IN
- **ALGORITHM**: `<<e.g. DEIO>>`
- **ALGORITHM_REPO**: `<<e.g. https://github.com/arclab-hku/DEIO>>`  (+ any Docker fork)
- **DATASET**: `<<e.g. VECtor>>`
- **DATASET_HOME**: `<<e.g. https://star-datasets.github.io/vector/>>`
- **SEQUENCES**: `<<e.g. the small-scale set, smallest first>>`
- **BASELINE_PAPERS** (with the table + metric): `<<e.g. DEIO arXiv:2411.03928 Table IV (MPE%, SE3-aligned); ESVIO arXiv:2212.13184 Table II>>`
- Target per sequence: **the best published number across the baseline papers**.

### Environment (this machine — don't re-discover)
- 2× RTX A5000 (24 GB), CUDA 12.2. **Deep/learned methods need the GPU + NVIDIA Container
  Toolkit; classical optimization methods are CPU-only.** Check `nvidia-smi`.
- Docker is installed but the shell session may lack the group: run docker as **`sg docker -c "..."`**.
  Privileged installs (nvidia-container-toolkit, apt) need the user's sudo password — **ask**.
- Python venv with evo/gdown/rosbags at **`~/.venvs/evtools`** (`$HOME/.venvs/evtools/bin/python`).
- Datasets are usually on Google Drive (`gdown`); large files hit a **download quota** — don't
  re-download needlessly, keep raw data, and if blocked ask the user to fetch via browser.
- Use **plan mode**, **persistent memory**, and **ask clarifying questions before** multi-GB
  downloads, long builds, or long runs.

### Non-negotiable principles
1. **Faithful to upstream.** Pin the upstream commit; make **zero edits to algorithm source**.
   If upstream ships a Dockerfile, vendor it verbatim and add only a pinned `git checkout`; else
   write one strictly following the repo's README build steps. Every deviation (headless launch,
   any config tuning) must be a **small, documented, opt-in flag — never silent**.
2. **Minimal, lossless preprocessing.** Feed the dataset in its native form (ROS bags preferred).
   Only topic remaps / message-type conversions needed to match the algorithm's subscribed types;
   **verify** them (message md5, event-count conservation). Repack the event representation only if
   the algorithm requires it, and then match the upstream's own tooling/rate.
3. **Transparent evaluation.** Report evo **ATE RMSE** *and* the paper's exact metric. For
   event-VIO papers this is almost always **MPE % = 100 × ATE-translation-RMSE / trajectory-length,
   with full-trajectory SE(3) alignment** — confirm the definition in the paper.
4. **Honest, faithful results.** Reproduce what the **authors intended** — do not tune to beat the
   paper. Legitimate config (calibration, IMU noise, keyframe policy) only to *match* it, documented;
   knobs that add capacity/compute (e.g. DEIO `PATCHES_PER_FRAME`) are **cheating**. If a sequence
   diverges or differs, say so and investigate before tuning. Never cherry-pick.
5. **Our own trajectories only.** Never use the authors' released trajectory files (uncertain
   provenance / possibly a different method variant). Produce and own every estimated trajectory,
   under one uniform methodology across all sequences — no per-sequence setups, never drop a sensor.
6. **SE3 (metric) for any method with metric info (IMU and/or stereo) — always.** Sim3 /
   scale-correction only for pure monocular-vision with no metric source; for inertial/stereo
   methods Sim3 hides scale failures (a free pass on the very thing the IMU/stereo provides).
   Always verify trajectory coverage (≥~97% of GT span) and raw scale before trusting a number.

### Folder structure to create/populate
Each algorithm is a self-contained top-level folder: the container + run scripts **and** its
per-dataset/sequence results live together under `{algo}/`.
```
{algo}/             Dockerfile, build.sh, run_{algo}.sh, run_in_container.sh,
                    run_and_eval.sh, launch/, README.md      (the algorithm itself)
{algo}/{dataset}/{seq}/   COMMITTED: stamped_traj.tum, {seq}_gt.txt, metrics.json,
                          trajectory_xy.pdf/.png, ape_translation.pdf/.png
datasets/{dataset}/ download_{dataset}.sh, import_{dataset}_bags.sh   (shared fetchers)
scripts/            evaluate.py, prophesee_to_dvs_bag.py    (shared tooling; reuse if present)
docs/validation/{algo}_{dataset}.md     our numbers vs the papers, honest
data/{dataset}/{seq}/    raw bags (gitignored)
```

### Step-by-step (in order)
1. **Algorithm recon** — read the actual repo (clone it shallow to a scratch dir and grep; don't
   trust memory): modality (mono/stereo, events-only/+frames/+IMU), required sensors, ROS version,
   deps, whether a Dockerfile exists, config + launch files (per-dataset?), **how it outputs the
   trajectory** (odometry topic name and/or a result CSV/TUM in `output_path`), the **message types
   it subscribes to** (get their md5 from generated headers), and any **GUI in the launch** (rviz/
   gnome-terminal) to make headless.
2. **Dataset recon** — distribution format, exact topic names + message types + rates, and crucially
   **whether 6-DoF trajectory ground truth exists** (some event datasets, e.g. DSEC, have none →
   only qualitative; pick sequences/datasets that have GT). Sizes; start with the smallest.
3. **Compatibility + plan** — modality must match (never feed mono data to a stereo method);
   resolve dataset↔config topic/type mismatches with minimal lossless adaptation; confirm the
   paper's metric + which sequences it reports. Write a plan, ask the user, get sign-off.
4. **Faithful Dockerfile** → `build.sh` → `event-world/{algo}:latest` (GPU base if learned method).
5. **Download** (`download_{dataset}.sh`) + verify any conversion (md5 + counts). Keep raw data.
6. **Headless run** (`run_in_container.sh`, mirror upstream's own run/record scripts if present):
   source ROS + workspace, set `ROS_MASTER_URI`/`ROS_HOSTNAME`; roscore → roslaunch headless nodes
   → `rosbag record` the odometry topic → `rosbag play` the bags (remaps if needed) →
   `evo_traj bag <odom> --save_as_tum` → `stamped_traj.tum`. Bind-mount results onto the config's
   `output_path` so the upstream yaml stays untouched.
7. **Evaluate** (`scripts/evaluate.py`, evo python API): timestamp-associate; SE(3) Umeyama align;
   ATE-translation RMSE; **MPE% = 100·RMSE/length**; rotation (note: a near-constant body-frame
   offset between the estimator's IMU frame and the GT frame is normal — remove it / use relative
   rotation). Write `metrics.json` + plots; archive `gt.txt` into results.
8. **Validate + document** — tabulate MPE% vs the best published number per sequence, honestly.
   **If results are ~2× too big or diverge, DON'T tune blindly — investigate first**: confirm the
   event conversion is lossless (events identical to the dataset's source file), IMU units/gravity,
   stereo L/R sync, that image/event features are actually fused, the metric/length, and that
   **rotation already matches the paper** (it usually does even when translation is off → the issue
   is scale/init, not the pipeline). The repeatedly-seen fix on well-calibrated datasets:
   **stop the online extrinsic/time-offset optimization** (`estimate_extrinsic:0`, `estimate_td:0`)
   and, if init still diverges, sweep init params (more features `max_cnt`/`max_cnt_img`, lower
   `keyframe_parallax`) — all as **documented, opt-in config overrides**, never silent edits.

### Deliverable
The populated folder above + a committed `docs/validation/{algo}_{dataset}.md` with our MPE% vs the
papers per sequence, the estimated trajectories and ground truth, plots, and an explicit list of any
documented deviations from upstream. Save durable facts (modality, metric, repo/commit, fixes) to
persistent memory as you go.

---
