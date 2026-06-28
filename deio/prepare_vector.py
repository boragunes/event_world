#!/usr/bin/env python3
"""Reconstruct DEIO's (unreleased) VECtor input layout from our VECtor rosbags.

DEIO ships a VECtor data *loader* (`utils.load_utils.vector_evs_iterator`) and splits,
but no eval script / config / preprocessing. This script produces, per sequence, the
exact files that loader + the inertial eval (`uzh-fpv.py` template) read:

  <out>/<scene>/
    <scene>.synced.left_event.hdf5   DSEC EventSlicer fmt: /x /y /p /t(us,rel) /ms_to_idx /t_offset
    rectify_map_left.h5              dataset 'rectify_map' (H,W,2): raw px -> undistorted px
    calib_undist_evs_left.txt        4 vals: fx fy cx cy (undistorted pinhole)
    tss_imgs_us_left.txt             left-image header timestamps (us) = voxel frame times
    imu.txt                          idx  ts(s)  gx gy gz (rad/s)  ax ay az (m/s^2)
    stamped_groundtruth_us.txt       ts(us) tx ty tz qx qy qz qw
    t0_us.txt                        0  (all VECtor streams already share one clock)

scene name follows DEIO's split, e.g. desk-normal -> desk_normal1.
NOT upstream-faithful: this is our reconstruction of the authors' pipeline.
"""
import argparse, os, struct, sys
import numpy as np
import h5py
import cv2
from rosbags.rosbag1 import Reader
from rosbags.highlevel import AnyReader
from pathlib import Path

# VECtor left event camera (from esvio_VECtor_small_scale/event0_esvio.yaml) — PINHOLE + radtan
K = np.array([[327.32749, 0, 304.97749], [0, 327.46184, 235.37621], [0, 0, 1]], np.float64)
DIST = np.array([-0.031982, 0.041966, -0.000507, -0.001031], np.float64)  # k1 k2 p1 p2
W, H = 640, 480

_3U32 = struct.Struct("<III")
_U32 = struct.Struct("<I")
EV = np.dtype({'names': ['x', 'y', 'sec', 'nsec', 'p'],
               'formats': ['<u2', '<u2', '<u4', '<u4', 'u1'],
               'offsets': [0, 2, 4, 8, 12], 'itemsize': 13})


def parse_events(raw):
    seq, sec, nsec = _3U32.unpack_from(raw, 0); off = 12
    (flen,) = _U32.unpack_from(raw, off); off += 4 + flen
    off += 8  # height, width
    (count,) = _U32.unpack_from(raw, off); off += 4
    return np.frombuffer(raw, dtype=EV, count=count, offset=off)


def read_events(bag):
    xs, ys, ps, ts = [], [], [], []
    with Reader(bag) as r:
        conns = [c for c in r.connections if c.msgtype.endswith("EventArray")]
        for con, t, raw in r.messages(connections=conns):
            e = parse_events(raw)
            if len(e) == 0:
                continue
            xs.append(e['x'].copy()); ys.append(e['y'].copy()); ps.append(e['p'].copy())
            ts.append(e['sec'].astype(np.int64) * 1_000_000 + e['nsec'].astype(np.int64) // 1000)
    return (np.concatenate(xs), np.concatenate(ys),
            np.concatenate(ps), np.concatenate(ts))


def write_event_h5(path, x, y, p, t_us):
    order = np.argsort(t_us, kind="stable")
    x, y, p, t_us = x[order], y[order], p[order], t_us[order]
    t_offset = int(t_us[0])
    t_rel = (t_us - t_offset).astype("<i8")
    max_ms = int(t_rel[-1] // 1000)
    ms_to_idx = np.searchsorted(t_rel, np.arange(max_ms + 1, dtype=np.int64) * 1000, side="left")
    with h5py.File(path, "w") as f:               # top-level datasets (DEIO EventSlicer else-branch)
        f.create_dataset("x", data=x.astype("<u2"), compression="lzf")
        f.create_dataset("y", data=y.astype("<u2"), compression="lzf")
        f.create_dataset("p", data=(p > 0).astype("u1"), compression="lzf")
        f.create_dataset("t", data=t_rel, compression="lzf")
        f.create_dataset("ms_to_idx", data=ms_to_idx.astype("<i8"))
        f.create_dataset("t_offset", data=np.int64(t_offset))
    return len(t_us), t_offset


def write_rectify(outdir):
    grid = np.stack(np.meshgrid(np.arange(W), np.arange(H)), -1).reshape(-1, 1, 2).astype(np.float32)
    und = cv2.undistortPoints(grid, K, DIST, R=np.eye(3), P=K).reshape(H, W, 2).astype(np.float32)
    with h5py.File(os.path.join(outdir, "rectify_map_left.h5"), "w") as f:
        f.create_dataset("rectify_map", data=und)
    np.savetxt(os.path.join(outdir, "calib_undist_evs_left.txt"),
               np.array([K[0, 0], K[1, 1], K[0, 2], K[1, 2]])[None], fmt="%.6f")


def read_image_tss_us(bag):
    tss = []
    with Reader(bag) as r:
        conns = [c for c in r.connections if c.msgtype.endswith("Image") or "image" in c.topic]
        for con, t, raw in r.messages(connections=conns):
            _, sec, nsec = _3U32.unpack_from(raw, 0)
            tss.append(sec * 1_000_000 + nsec // 1000)
    return np.array(sorted(tss), dtype=np.int64)


def read_imu(bag, out):
    rows = []
    with AnyReader([Path(bag)]) as r:
        conns = [c for c in r.connections if c.msgtype.endswith("Imu")]
        for con, t, raw in r.messages(connections=conns):
            m = r.deserialize(raw, con.msgtype)
            ts = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
            g, a = m.angular_velocity, m.linear_acceleration
            rows.append((ts, g.x, g.y, g.z, a.x, a.y, a.z))
    rows.sort()
    with open(out, "w") as f:
        for i, (ts, gx, gy, gz, ax, ay, az) in enumerate(rows):
            f.write(f"{i} {ts:.9f} {gx:.9f} {gy:.9f} {gz:.9f} {ax:.9f} {ay:.9f} {az:.9f}\n")
    return len(rows)


def write_gt_us(gt_txt, out):
    g = np.loadtxt(gt_txt)                          # TUM: ts(s) tx ty tz qx qy qz qw
    g[:, 0] *= 1e6                                  # -> us
    np.savetxt(out, g, fmt=["%d"] + ["%.9f"] * 7)
    return len(g)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seq")                          # e.g. desk-normal
    ap.add_argument("--data", default="data/vector")
    ap.add_argument("--out", default="data/deio_vector")
    a = ap.parse_args()
    scene = a.seq.replace("-", "_") + "1"           # desk-normal -> desk_normal1 (DEIO split name)
    sd = f"{a.data}/{a.seq}"
    od = f"{a.out}/{scene}"; os.makedirs(od, exist_ok=True)
    print(f"[{a.seq}] -> {od}")

    x, y, p, t = read_events(f"{sd}/{a.seq}_left_event.bag")
    n, t0 = write_event_h5(f"{od}/{scene}.synced.left_event.hdf5", x, y, p, t)
    print(f"  events: {n}  span {(t[-1]-t[0])/1e6:.1f}s  t_offset={t0}")
    write_rectify(od)
    tss = read_image_tss_us(f"{sd}/{a.seq}_left_camera.bag")
    np.savetxt(f"{od}/tss_imgs_us_left.txt", tss, fmt="%d")
    print(f"  images: {len(tss)}  ({np.mean(np.diff(tss))/1e3:.1f} ms mean dt)")
    ni = read_imu(f"{sd}/{a.seq}_imu.bag", f"{od}/imu.txt")
    ng = write_gt_us(f"{sd}/{a.seq}_gt_txt.txt", f"{od}/stamped_groundtruth_us.txt")
    open(f"{od}/t0_us.txt", "w").write("0\n")
    print(f"  imu: {ni}  gt: {ng}  -> done")


if __name__ == "__main__":
    sys.exit(main())
