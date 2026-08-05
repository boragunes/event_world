#!/usr/bin/env python3
"""SE(3)-only reference table for the metric (scale-recovering) baselines.

Scope decision: DUET-VO is stereo and recovers metric scale, so the like-for-like
comparison set is limited to methods that also recover scale without external help.
Monocular up-to-scale results (DEVO, DPVO, monocular ORB-SLAM3) and any Sim(3) or
scale-corrected row are excluded -- they are not the same quantity.

Where several papers publish an SE(3) value for the same method+sequence we keep the
BEST (lowest ATE). That is the conspicuously-generous choice of RESUBMISSION_PLAN
section 6.3: beating a baseline at its strongest published showing is unimpeachable.

Usage: scripts/make_se3_reference.py > docs/se3_reference.md
"""
import csv
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METHODS = ["Stereo-DEVO", "ESVO2", "ESVIO", "ESIO", "DEIO", "ES-PTAM"]

# our runs, VECtor only so far
OURS_DIR = {"Stereo-DEVO": "sdevo/vector", "ESVO2": "esvo2/vector", "ESVIO": "esvio/vector",
            "ESIO": "esvio/vector-esio", "DEIO": "deio/vector"}
DIVERGED_MPE_PCT, MIN_COVERAGE_PCT = 30.0, 10.0

# plan inventory (section 3.4); VECtor names use our hyphenated form
PLAN = [
    ("RPG", ["rpg_box", "rpg_monitor", "rpg_bin", "rpg_desk", "rpg_reader"]),
    ("MVSEC", ["indoor_flying1", "indoor_flying2", "indoor_flying3", "indoor_flying4"]),
    ("DSEC", ["city04_a", "city04_b", "city04_c", "city04_d", "city09_a", "city09_b",
              "city09_c", "city09_d", "city09_e", "city11_a", "city11_b"]),
    ("VECtor", ["corner_slow", "robot_normal", "desk_normal", "sofa_normal", "hdr_normal",
                "corridors_dolly", "units_dolly"]),
    ("TUM-VIE", ["tumvie_1d_trans", "tumvie_3d_trans", "tumvie_6dof", "tumvie_desk",
                 "tumvie_desk2"]),
    ("Other", ["hnu_campus", "drone_fast"]),
]
# VECtor sequences we ran that are outside the plan inventory
VECTOR_EXTRA = ["mountain_normal", "robot_fast", "desk_fast", "sofa_fast", "hdr_fast",
                "mountain_fast"]


def is_se3(x):
    a = (x["alignment"] or "").lower()
    return x["metric_type"] == "metric" and "sim3" not in a and "scale-corrected" not in a


def load_best():
    """(dataset, seq, method) -> (best_value, source_paper). SE(3) metric ATE only."""
    best = {}
    for x in csv.DictReader(open(f"{ROOT}/results_db/results.csv")):
        if x["method"] not in METHODS or x["metric"] != "ATE" or not x["value"]:
            continue
        if not is_se3(x):
            continue
        k = (x["dataset"], x["sequence_norm"] or x["sequence"], x["method"])
        v = float(x["value"])
        if k not in best or v < best[k][0]:
            best[k] = (v, x["paper_short"])
    return best


def our_run(method, seq):
    """-> (text, ok) for a VECtor sequence we ran ourselves."""
    d = OURS_DIR.get(method)
    if not d:
        return None
    s = seq.replace("_", "-")
    mp = f"{ROOT}/{d}/{s}/metrics.json"
    if not os.path.exists(mp):
        return None
    m = json.load(open(mp))
    ate = m["ate_translation_m"]["rmse"] * 100
    mpe = m["paper_metric"]["MPE_percent_ate"]
    traj = f"{ROOT}/{d}/{s}/stamped_traj.tum"
    cov = float("nan")
    if os.path.exists(traj):
        e = np.loadtxt(traj)
        if len(e) > 2:
            g = np.loadtxt(f"{ROOT}/data/deio_vector/{s.replace('-', '_')}1/poses_evs_left.txt")
            cov = 100 * (e[-1, 0] - e[0, 0]) / (g[-1, 0] - g[0, 0])
    if not np.isnan(cov) and cov < MIN_COVERAGE_PCT:
        return ("`ni`", False)
    if mpe > DIVERGED_MPE_PCT:
        return ("`div`", False)
    return (f"{ate:.2f}", True)


LIT_ONLY = "--lit-only" in __import__("sys").argv

if __name__ == "__main__":
    best = load_best()
    print("# SE(3) reference table — metric baselines only\n")
    print("Scope: methods that recover metric scale without external help, which is the")
    print("like-for-like set for a stereo submission. Monocular up-to-scale results (DEVO,")
    print("DPVO, mono ORB-SLAM3) and every Sim(3)/scale-corrected row are excluded.\n")
    print("Published values are the **best** SE(3) ATE across all papers reporting that")
    print("method+sequence (section 6.3: beat a baseline at its strongest showing). ATE in cm.\n")
    print("Cell key: **bold** = our own SE(3) run · plain = published only, we have not run it ·")
    print("`div` / `ni` = we ran it, it diverged / never initialised · — = no published value.\n")

    have = notrun = nolit = 0
    for ds, seqs in PLAN:
        print(f"\n## {ds}\n")
        print("| sequence | " + " | ".join(METHODS) + " | staged |")
        print("|---" * (len(METHODS) + 2) + "|")
        for s in seqs:
            cells = []
            for m in METHODS:
                ours = None if LIT_ONLY else (our_run(m, s) if ds == "VECtor" else None)
                lit = best.get((ds, s, m))
                if ours:
                    cells.append(f"**{ours[0]}**")
                    have += 1
                elif lit:
                    cells.append(f"{lit[0]:.2f}")
                    notrun += 1
                else:
                    cells.append("—")
                    nolit += 1
            staged = "✅" if (ds == "VECtor" and os.path.isdir(
                f"{ROOT}/data/vector/{s.replace('_', '-')}")) else "⬜"
            print(f"| {s} | " + " | ".join(cells) + f" | {staged} |")

    print("\n## VECtor — sequences we ran beyond the plan inventory\n")
    print("| sequence | " + " | ".join(METHODS) + " | staged |")
    print("|---" * (len(METHODS) + 2) + "|")
    for s in VECTOR_EXTRA:
        cells = []
        for m in METHODS:
            ours = None if LIT_ONLY else our_run(m, s)
            lit = best.get(("VECtor", s, m))
            cells.append(f"**{ours[0]}**" if ours else (f"{lit[0]:.2f}" if lit else "—"))
        print(f"| {s} | " + " | ".join(cells) + " | ✅ |")

    total = have + notrun + nolit
    print(f"\n## Summary — plan inventory only ({len(METHODS)} methods × 34 sequences = {total} cells)\n")
    print(f"- **{have}** cells we have run ourselves ({100*have/total:.0f} %)")
    print(f"- **{notrun}** cells with a published SE(3) value but no run of ours ({100*notrun/total:.0f} %)")
    print(f"- **{nolit}** cells with neither ({100*nolit/total:.0f} %) — must be self-run or carry a reason code")
