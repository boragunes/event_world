#!/usr/bin/env python3
"""Evaluate an estimated trajectory (TUM) against ground truth (TUM) with evo.

Reports the standard evo ATE (RMSE etc.) AND the metric the ESVIO paper uses:
  MPE (%)  = 100 * ATE_translation_RMSE / ground-truth-trajectory-length
  MRE      = mean absolute rotation error (deg), also normalised per metre
so our numbers can be compared apples-to-apples with the paper's Table II.

Writes <out-dir>/metrics.json plus trajectory and error plots.

Usage:
  evaluate.py --dataset vector --seq desk-normal
  evaluate.py --est path/to/est.tum --gt path/to/gt.txt --out-dir DIR --label name
"""
import argparse
import copy
import json
import os
from datetime import datetime, timezone

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import evo
from evo.core import metrics, sync
from evo.core.trajectory import PoseTrajectory3D
from evo.tools import plot

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_tum(path):
    """Load a TUM file (t tx ty tz qx qy qz qw); tolerant of '#' comment lines."""
    d = np.loadtxt(path, comments="#")
    if d.ndim == 1:
        d = d.reshape(1, -1)
    t = d[:, 0]
    xyz = d[:, 1:4]
    q_xyzw = d[:, 4:8]
    q_wxyz = q_xyzw[:, [3, 0, 1, 2]]
    return PoseTrajectory3D(positions_xyz=xyz, orientations_quat_wxyz=q_wxyz, timestamps=t)


def ape(ref, est, relation):
    m = metrics.APE(relation)
    m.process_data((ref, est))
    return m


def rpe(ref, est, relation, delta=1.0):
    m = metrics.RPE(relation, delta=delta, delta_unit=metrics.Unit.meters, all_pairs=True)
    m.process_data((ref, est))
    return m


def estimate_body_offset(est, ref):
    """Constant rotation R s.t. R_est_i @ R best matches R_gt_i (sensor-to-GT
    body-frame extrinsic). Chordal-L2 rotation average via SVD."""
    M = np.zeros((3, 3))
    for pe, pg in zip(est.poses_se3, ref.poses_se3):
        M += pe[:3, :3].T @ pg[:3, :3]
    U, _, Vt = np.linalg.svd(M)
    R = U @ Vt
    if np.linalg.det(R) < 0:
        U[:, -1] *= -1
        R = U @ Vt
    return R


def apply_body_offset(est, R):
    """Right-multiply each pose's rotation by R (keep positions)."""
    poses = []
    for p in est.poses_se3:
        q = p.copy()
        q[:3, :3] = p[:3, :3] @ R
        poses.append(q)
    return PoseTrajectory3D(poses_se3=poses, timestamps=est.timestamps)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset")
    ap.add_argument("--seq")
    ap.add_argument("--algo", default="esvio")
    ap.add_argument("--est")
    ap.add_argument("--gt")
    ap.add_argument("--out-dir")
    ap.add_argument("--label")
    ap.add_argument("--align", choices=["se3", "sim3", "none"], default="se3")
    ap.add_argument("--t-max-diff", type=float, default=0.02)
    a = ap.parse_args()

    if a.dataset and a.seq:
        a.est = a.est or f"{REPO}/{a.algo}/{a.dataset}/{a.seq}/stamped_traj.tum"
        a.out_dir = a.out_dir or f"{REPO}/{a.algo}/{a.dataset}/{a.seq}"
        a.label = a.label or f"{a.algo}/{a.dataset}/{a.seq}"
        if not a.gt and a.dataset == "vector":
            a.gt = f"{REPO}/data/{a.dataset}/{a.seq}/{a.seq}_gt_txt.txt"
    if not (a.est and a.gt and a.out_dir):
        ap.error("need --est, --gt, --out-dir (or --dataset/--seq)")
    os.makedirs(a.out_dir, exist_ok=True)

    ref = load_tum(a.gt)
    est = load_tum(a.est)
    n_est_raw = est.num_poses
    ref, est = sync.associate_trajectories(ref, est, max_diff=a.t_max_diff)

    est_aligned = copy.deepcopy(est)
    if a.align != "none":
        est_aligned.align(ref, correct_scale=(a.align == "sim3"))

    length = float(ref.path_length)
    duration = float(ref.timestamps[-1] - ref.timestamps[0])

    # World-frame SE3 alignment (above) fixes the global frame, but the estimator
    # body frame (IMU) and the mocap GT body frame differ by a fixed rotation
    # (sensor-to-marker extrinsic). Estimate & remove it; otherwise ABSOLUTE
    # rotation error is a ~constant offset and RPE is corrupted (relative motion
    # expressed in a rotated frame). Translation/ATE is unaffected by this.
    Rbe = estimate_body_offset(est_aligned, ref)
    body_offset_deg = float(np.degrees(np.arccos(np.clip((np.trace(Rbe) - 1) / 2, -1, 1))))
    est_bc = apply_body_offset(est_aligned, Rbe)

    ape_t = ape(ref, est_aligned, metrics.PoseRelation.translation_part)
    ape_r = ape(ref, est_bc, metrics.PoseRelation.rotation_angle_deg)
    st = ape_t.get_all_statistics()
    sr = ape_r.get_all_statistics()

    # Relative drift over 1 m segments (rpg-style), on the body-frame-corrected est.
    delta_m = 1.0
    rel_trans_pct = rel_rot_dpm = float("nan")
    try:
        rpe_t = rpe(ref, est_bc, metrics.PoseRelation.translation_part, delta_m)
        rpe_r = rpe(ref, est_bc, metrics.PoseRelation.rotation_angle_deg, delta_m)
        rel_trans_pct = 100.0 * float(np.mean(rpe_t.error)) / delta_m
        rel_rot_dpm = float(np.mean(rpe_r.error)) / delta_m
    except Exception as e:
        print(f"WARN: RPE failed: {e}")

    ate_rmse = float(st["rmse"])
    mpe_abs_pct = 100.0 * ate_rmse / length if length > 0 else float("nan")

    metrics_out = {
        "label": a.label,
        "algo": a.algo, "dataset": a.dataset, "sequence": a.seq,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evo_version": evo.__version__,
        "est_file": os.path.relpath(a.est, REPO),
        "gt_file": os.path.relpath(a.gt, REPO),
        "alignment": a.align,
        "n_poses_matched": int(ref.num_poses),
        "n_poses_est_raw": int(n_est_raw),
        "gt_trajectory_length_m": round(length, 4),
        "duration_s": round(duration, 3),
        "ate_translation_m": {k: round(float(v), 6) for k, v in st.items()},
        "rotation_deg": {
            "body_frame_offset_deg": round(body_offset_deg, 3),
            "residual_after_offset": {k: round(float(v), 6) for k, v in sr.items()},
            "note": "absolute orientation error AFTER removing the constant estimator-vs-GT body-frame offset",
        },
        "paper_metric": {
            "MPE_percent_ate": round(mpe_abs_pct, 4),
            "MPE_percent_rel_1m": round(rel_trans_pct, 4),
            "MRE_deg_per_m_rel_1m": round(rel_rot_dpm, 5),
            "note": ("MPE_ate = 100*ATE_trans_RMSE/length (paper SE3 convention); "
                     "*_rel_1m = mean drift over 1 m segments after body-frame correction"),
        },
    }
    with open(os.path.join(a.out_dir, "metrics.json"), "w") as f:
        json.dump(metrics_out, f, indent=2)

    # --- plots ---
    try:
        fig = plt.figure(figsize=(8, 8))
        ax = plot.prepare_axis(fig, plot.PlotMode.xy)
        plot.traj(ax, plot.PlotMode.xy, ref, style="--", color="gray", label="ground truth")
        plot.traj(ax, plot.PlotMode.xy, est_aligned, color="blue", label="ESVIO (aligned)")
        ax.set_title(f"{a.label}  ATE RMSE={ate_rmse:.3f} m  MPE(rel)={rel_trans_pct:.2f}%")
        ax.legend()
        fig.savefig(os.path.join(a.out_dir, "trajectory_xy.png"), dpi=120, bbox_inches="tight")
        fig.savefig(os.path.join(a.out_dir, "trajectory_xy.pdf"), bbox_inches="tight")
        plt.close(fig)

        fig = plt.figure(figsize=(10, 4))
        t = ref.timestamps - ref.timestamps[0]
        plt.plot(t, ape_t.error, color="red")
        plt.xlabel("t [s]"); plt.ylabel("APE translation [m]")
        plt.title(f"{a.label} — APE over time")
        plt.grid(True, alpha=0.3)
        fig.savefig(os.path.join(a.out_dir, "ape_translation.png"), dpi=120, bbox_inches="tight")
        fig.savefig(os.path.join(a.out_dir, "ape_translation.pdf"), bbox_inches="tight")
        plt.close(fig)
    except Exception as e:  # plotting must never block metrics
        print(f"WARN: plotting failed: {e}")

    print(json.dumps(metrics_out, indent=2))
    print(f"\n-> {a.out_dir}/metrics.json  (+ trajectory_xy.png, ape_translation.png)")


if __name__ == "__main__":
    main()
