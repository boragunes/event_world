#!/usr/bin/env python3
"""Generate the two provenance-separated tables required by RESUBMISSION_PLAN section 6.1,
across every dataset we hold data or literature for.

Table A -- every cell run by us, protocol disclosed, raw trajectories released.
Table B -- literature, cited, alignment/accumulation conventions differ between sources.

The separation is the point: the provenance boundary must be a table border, not a
diagonal through one table. Reason codes (section 6.1): div ran/diverged, nc no public
code, ng no ground truth, oom resource limit, ns sensor modality absent.

Usage: scripts/make_provenance_tables.py > docs/resubmission_tables.md
"""
import csv
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Methods in plan order: Table A candidates first, then Table B / context methods.
METHODS = ["DUET-VO", "Stereo-DEVO", "DEIO", "ESVIO", "ESIO", "ESVO2", "DEVO", "ESVO", "ES-PTAM"]

# our runs: display name -> (results dir, alignment). Stereo-DEVO is S-DEVO.
OURS_DIR = {
    "Stereo-DEVO": ("sdevo/vector", "se3"),
    "DEIO": ("deio/vector", "se3"),
    "ESVIO": ("esvio/vector", "se3"),
    "ESIO": ("esvio/vector-esio", "se3"),
    "ESVO2": ("esvo2/vector", "se3"),
    "DEVO": ("devo/vector", "sim3"),
}

# datasets in the plan's benchmark inventory (section 3.4) -> sequences required
PLAN_DATASETS = {
    "RPG": 5, "MVSEC": 4, "DSEC": 11, "VECtor": 7, "TUM-VIE": 5, "Other": 2, "M3ED": 13,
}

VECTOR_IN_PLAN = ["corner-slow", "robot-normal", "desk-normal", "sofa-normal", "hdr-normal"]
VECTOR_BONUS = ["mountain-normal", "robot-fast", "desk-fast", "sofa-fast", "hdr-fast",
                "mountain-fast"]

DIVERGED_MPE_PCT = 30.0   # MPE above this share of path length is divergence, not measurement
MIN_COVERAGE_PCT = 10.0   # below this the trajectory is a fragment; any ATE is meaningless


def gt_span(seq):
    g = np.loadtxt(f"{ROOT}/data/deio_vector/{seq.replace('-', '_')}1/poses_evs_left.txt")
    return g[-1, 0] - g[0, 0]


def cell(algo_dir, seq):
    """-> (text, verdict) for one Table A cell."""
    mp = f"{ROOT}/{algo_dir}/{seq}/metrics.json"
    if not os.path.exists(mp):
        return "—", "not-run"
    m = json.load(open(mp))
    ate = m["ate_translation_m"]["rmse"] * 100
    mpe = m["paper_metric"]["MPE_percent_ate"]
    traj = f"{ROOT}/{algo_dir}/{seq}/stamped_traj.tum"
    cov = float("nan")
    if os.path.exists(traj):
        e = np.loadtxt(traj)
        if len(e) > 2:
            cov = 100 * (e[-1, 0] - e[0, 0]) / gt_span(seq)
    if not np.isnan(cov) and cov < MIN_COVERAGE_PCT:
        return "`ni`", "no-init"
    if mpe > DIVERGED_MPE_PCT:
        return "`div`", "diverged"
    return f"{ate:.2f}", "ok"


def load_lit():
    rows = list(csv.DictReader(open(f"{ROOT}/results_db/results.csv")))
    lit = {}          # (dataset, seq, method) -> {paper: value}   ATE only, for numeric compare
    cov = {}          # (dataset, seq, method) -> set(metric)       any metric, for coverage
    seqs = {}         # dataset -> set(seq)
    for x in rows:
        # ATE and MPE are both first-class in this literature: MPE is the more common
        # of the two (1569 vs 1075 rows), so counting only ATE hides whole datasets.
        if not x["value"] or x["metric"] not in ("ATE", "MPE"):
            continue
        sn = (x["sequence_norm"] or x["sequence"]).replace("_", "-")
        cov.setdefault((x["dataset"], sn, x["method"]), set()).add(x["metric"])
        if x["metric"] == "ATE":
            lit.setdefault((x["dataset"], sn, x["method"]), {})[x["paper_short"]] = x["value"]
        seqs.setdefault(x["dataset"], set()).add(sn)
    return lit, cov, seqs


def overview(cov, seqs):
    """Dataset x method coverage: ours vs literature, every dataset."""
    datasets = sorted(seqs) + ["M3ED"]
    a_out = ["| dataset | in plan | seqs staged | " + " | ".join(METHODS) + " |",
             "|---" * (len(METHODS) + 3) + "|"]
    b_out = ["| dataset | " + " | ".join(METHODS) + " | distinct seqs |",
             "|---" * (len(METHODS) + 2) + "|"]
    for d in datasets:
        # --- Table A row: how many sequences we ran, per method
        a_cells = []
        for meth in METHODS:
            if d == "VECtor" and meth in OURS_DIR:
                n = sum(1 for s in VECTOR_IN_PLAN + VECTOR_BONUS
                        if os.path.exists(f"{ROOT}/{OURS_DIR[meth][0]}/{s}/metrics.json"))
                a_cells.append(f"**{n}**" if n else "·")
            else:
                a_cells.append("·")
        staged = "11" if d == "VECtor" else "0"
        inplan = f"{PLAN_DATASETS[d]}" if d in PLAN_DATASETS else "—"
        a_out.append(f"| {d} | {inplan} | {staged} | " + " | ".join(a_cells) + " |")
        # --- Table B row: how many sequences have published numbers, per method
        b_cells = []
        for meth in METHODS:
            n = len({s for (dd, s, mm) in cov if dd == d and mm == meth})
            b_cells.append(str(n) if n else "·")
        b_out.append(f"| {d} | " + " | ".join(b_cells) + f" | {len(seqs.get(d, []))} |")
    return "\n".join(a_out), "\n".join(b_out)


def vector_detail():
    cols = [m for m in METHODS if m in OURS_DIR]
    out = ["| sequence | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    tally = {"ok": 0, "diverged": 0, "no-init": 0, "not-run": 0}
    for group, ss in [("in S-DEVO inventory", VECTOR_IN_PLAN), ("our extra coverage", VECTOR_BONUS)]:
        out.append(f"| *{group}* |" + " |" * len(cols))
        for s in ss:
            cells = []
            for meth in cols:
                txt, v = cell(OURS_DIR[meth][0], s)
                tally[v] += 1
                cells.append(txt)
            out.append(f"| {s} | " + " | ".join(cells) + " |")
    return "\n".join(out), tally


def discrepancies(lit):
    out = []
    for s in VECTOR_IN_PLAN + VECTOR_BONUS:
        for meth, (d, _) in OURS_DIR.items():
            txt, verdict = cell(d, s)
            if verdict != "ok":
                continue
            for paper, val in lit.get(("VECtor", s, meth), {}).items():
                ours, theirs = float(txt), float(val)
                if theirs <= 0:
                    continue
                ratio = max(ours, theirs) / min(ours, theirs)
                if ratio >= 3.0:
                    out.append((s, meth, ours, theirs, paper, ratio))
    return sorted(out, key=lambda r: -r[5])


if __name__ == "__main__":
    lit, cov, seqs = load_lit()
    a_ov, b_ov = overview(cov, seqs)
    det, tally = vector_detail()

    print("# DUET-VO → RA-L: Table A / Table B, all datasets\n")
    print("Auto-generated by `scripts/make_provenance_tables.py` from this repository's runs")
    print("and from `results_db/` (papers extracted into a machine-readable database).\n")

    print("## 1. Table A — reproduced by us (coverage)\n")
    print("Number of sequences we have run ourselves, per dataset per method.")
    print("`in plan` = sequences the plan's section 3.4 inventory requires.\n")
    print(a_ov)
    print("\n**Only VECtor is populated.** Every other dataset is unstaged, so Table A is empty")
    print("there — that is the whole of the remaining work, and it is data staging plus compute")
    print("rather than new engineering: six algorithms are already containerised and validated.\n")

    print("## 2. Table B — literature (coverage)\n")
    print("Number of sequences with a published ATE **or** MPE we have already extracted.\n")
    print(b_ov)
    print("\nThe literature database is far broader than the plan requires: it covers 16 datasets")
    print("and 69 methods in total, including ECD, EDS, HKU, UZH-FPV and Mono-HKU, which are")
    print("outside the S-DEVO inventory but available if a reviewer asks for wider context.\n")

    print("## 3. Table A detail — VECtor, the one dataset we have run\n")
    print("ATE in cm, SE(3) alignment except DEVO (monocular, Sim(3); **not** scale-comparable).")
    print("Ground truth is the exact event-camera frame throughout. Reason codes: `div` ran and")
    print("diverged · `ni` ran, never initialised (fragment; any ATE would be meaningless).\n")
    print(det)
    print(f"\n{tally['ok']} measured · {tally['diverged']} diverged · {tally['no-init']} never "
          f"initialised · {tally['not-run']} not attempted ({sum(tally.values())} cells).\n")

    d = discrepancies(lit)
    if d:
        print("## 4. Where our run disagrees with a published quote (≥3×)\n")
        print("Bidirectional by construction: rows where we do better and rows where we do worse.\n")
        print("| sequence | method | ours | quoted | quoted by | ratio |")
        print("|---|---|---|---|---|---|")
        for s, meth, ours, theirs, paper, ratio in d:
            print(f"| {s} | {meth} | {ours:.2f} | {theirs:.2f} | {paper} | {ratio:.0f}× |")
