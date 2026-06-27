#!/usr/bin/env python3
"""Compare algorithms under DEIO's *published* evaluation logic, for an apples-to-apples
table when one method (DEIO) reports scale-corrected results.

DEIO's eval (utils/eval_utils.py in arclab-hku/DEIO) computes, per sequence:
    gtlen   = gt.get_infos()["path length (m)"]
    gt, est = sync.associate_trajectories(gt, est, max_diff=1)
    ape     = main_ape.ape(gt, est, pose_relation=translation_part,
                           align=True, correct_scale=True)      # Sim3
    MPE     = ape.stats["mean"] / gtlen * 100                   # MEAN, not RMSE

We replicate that exactly. Sim3 (correct_scale=True) hides scale errors, which is the
point for learned up-to-scale methods — but it can also *mask a diverged estimate* by
shrinking it to a point near the GT centroid (then mean/length looks small because the
path is long). We flag that: after Sim3 alignment, if the estimate's spatial extent is
< 0.5x the GT's, the track collapsed -> report FAIL, not the artifact number.

Usage: compare_deio_logic.py [dataset] [algo ...]    (default: vector esvio deio)
"""
import sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from evaluate import load_tum
from evo.core import sync, metrics
import evo.main_ape as main_ape

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTENT = lambda t: float(np.linalg.norm(t.positions_xyz.max(0) - t.positions_xyz.min(0)))


def deio_eval(gt_path, est_path):
    """Return (MPE%, collapsed_bool, extent_ratio) using DEIO's exact logic."""
    ref, est = load_tum(gt_path), load_tum(est_path)
    gtlen = float(ref.get_infos()["path length (m)"])
    ref, est = sync.associate_trajectories(ref, est, max_diff=1)
    aligned = copy.deepcopy(est); aligned.align(ref, correct_scale=True)
    ratio = EXTENT(aligned) / EXTENT(ref) if EXTENT(ref) > 0 else 0.0
    ape = main_ape.ape(copy.deepcopy(ref), copy.deepcopy(est),
                       pose_relation=metrics.PoseRelation.translation_part,
                       align=True, correct_scale=True)
    return ape.stats["mean"] / gtlen * 100, (ratio < 0.5), ratio


def main():
    a = sys.argv[1:]
    dataset = a[0] if a else "vector"
    algos = a[1:] if len(a) > 1 else ["esvio", "deio"]
    seqs = sorted(d for d in os.listdir(f"{REPO}/{algos[0]}/{dataset}")
                  if os.path.isdir(f"{REPO}/{algos[0]}/{dataset}/{d}"))
    w = {al: 0 for al in algos}
    print("DEIO-logic (Sim3, MPE=mean/len*100, max_diff=1); FAIL = collapsed estimate\n")
    print(f"{'sequence':16} " + " ".join(f"{al:>10}" for al in algos) + "   winner")
    for s in seqs:
        gt = f"{REPO}/data/{dataset}/{s}/{s}_gt_txt.txt"
        if not os.path.exists(gt):
            gt = f"{REPO}/{algos[0]}/{dataset}/{s}/{s}_gt.txt"
        cells, vals = {}, {}
        for al in algos:
            est = f"{REPO}/{al}/{dataset}/{s}/stamped_traj.tum"
            if not os.path.exists(est):
                cells[al] = "-"; continue
            mpe, collapsed, _ = deio_eval(gt, est)
            cells[al] = "FAIL" if collapsed else f"{mpe:.2f}%"
            if not collapsed:
                vals[al] = mpe
        win = min(vals, key=vals.get) if vals else ""
        if win:
            w[win] += 1
        print(f"{s:16} " + " ".join(f"{cells.get(al,'-'):>10}" for al in algos) + f"   {win}")
    print("\nwins: " + ", ".join(f"{al}={w[al]}" for al in algos))


if __name__ == "__main__":
    main()
