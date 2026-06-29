#!/usr/bin/env python3
"""Base DEVO (dpvo-clean) on VECtor, using tum-vision/DEVO's VECtor evaluation pipeline:
  - per-sequence frame crop  (get_imstart_imstop_vector)
  - voxel window [ts, ts+dT_ms] at the image/frame timestamps; dT_ms = imgdt*2 (slow) / /2 (fast)
  - DSEC EventSlicer for event slicing, rectify-map rectification
  - event-camera-frame GT (poses_evs_left)  ->  vision-only, so Sim3 (correct_scale) eval
DEVO model + voxel are dpvo-clean's; the data pipeline is faithfully DEVO's.
Data dir per scene: <scene>.synced.left_event.hdf5, rectify_map_left.h5,
calib_undist_evs_left.txt, tss_imgs_us_left.txt, poses_evs_left.txt.
"""
import os, glob, math, copy, argparse, json
import numpy as np
import torch
import h5py
import evo.main_ape as main_ape
from evo.core import sync, metrics
from evo.core.trajectory import PoseTrajectory3D

from dpvo.config import cfg
from dpvo.devo import DEVO
from dpvo.event import to_voxel_grid_cuda, get_time_indices_offsets

H, W = 480, 640

# DEVO's per-sequence crop (utils/load_utils.py get_imstart_imstop_vector), keyed by scene name
CROP = {'corner_slow': (30, 1180), 'robot_normal': (40, -1), 'robot_fast': (30, 901),
        'desk_normal': (65, -1), 'desk_fast': (25, 1380), 'sofa_normal': (120, 2700),
        'sofa_fast': (50, 1200), 'mountain_normal': (40, -1), 'mountain_fast': (15, 1290),
        'hdr_normal': (30, -1), 'hdr_fast': (35, -1)}


def get_crop(scene):
    for k, (a, b) in CROP.items():
        if k in scene:
            return a, b
    return 0, -1


class EventSlicer:
    """DSEC EventSlicer (tum-vision/DEVO utils/event_utils.py), self-contained."""
    def __init__(self, h5f):
        keys = list(h5f.keys())
        grp = 'events/' if 'events' in keys else ''
        self.ev = {d: h5f[grp + d] for d in ['p', 'x', 'y', 't']}
        self.ms_to_idx = np.asarray(h5f['ms_to_idx'], dtype='int64')
        self.t_offset = int(np.asarray(h5f['t_offset']).flatten()[0]) if 't_offset' in keys else 0

    def ms2idx(self, ms):
        return int(self.ms_to_idx[ms]) if 0 <= ms < self.ms_to_idx.size else None

    def get_events(self, t0_us, t1_us):
        t0_us -= self.t_offset
        t1_us -= self.t_offset
        i0 = self.ms2idx(max(int(math.floor(t0_us / 1000)), 0))
        i1 = self.ms2idx(int(math.ceil(t1_us / 1000)))
        if i0 is None or i1 is None or i1 <= i0:
            return None
        t = np.asarray(self.ev['t'][i0:i1]).astype(np.int64)
        o0, o1 = get_time_indices_offsets(t, int(t0_us), int(t1_us))
        if o1 <= o0:
            return None
        out = {'t': t[o0:o1] + self.t_offset}
        for d in ['p', 'x', 'y']:
            out[d] = np.asarray(self.ev[d][i0 + o0:i0 + o1])
        return out


@torch.no_grad()
def run_scene(scene_dir, net, dT_ms=None):
    intr = np.loadtxt(os.path.join(scene_dir, 'calib_undist_evs_left.txt'))
    with h5py.File(os.path.join(scene_dir, 'rectify_map_left.h5'), 'r') as f:
        rmap = f['rectify_map'][:]
    h5 = h5py.File(glob.glob(os.path.join(scene_dir, '*.synced.left_event.hdf5'))[0], 'r')
    slicer = EventSlicer(h5)
    tss = np.loadtxt(os.path.join(scene_dir, 'tss_imgs_us_left.txt'))
    if dT_ms is None:
        dT_ms = float(np.mean(np.diff(tss)) / 1e3)
    dT_ms = dT_ms / 2.0 if 'fast' in scene_dir else dT_ms * 2.0
    a, b = get_crop(os.path.basename(scene_dir))
    tss = tss[a:b]
    print(f"  {os.path.basename(scene_dir)}: {len(tss)} frames, dT_ms={dT_ms:.2f}, crop=({a},{b})")

    slam = DEVO(cfg, net, ht=H, wd=W)
    for ts in tss:
        t0, t1 = ts, ts + dT_ms * 1e3
        ev = slicer.get_events(t0, t1)
        if ev is None or len(ev['t']) == 0:
            continue
        rect = rmap[ev['y'], ev['x']]
        voxel = to_voxel_grid_cuda(np.ascontiguousarray(rect[..., 0]),
                                   np.ascontiguousarray(rect[..., 1]),
                                   ev['t'].astype(np.int64), ev['p'], H, W, 5)
        slam((t0 + t1) / 2 / 1e6, torch.from_numpy(voxel).cuda(),
             torch.from_numpy(intr).cuda())
    poses, tstamps = slam.terminate()
    h5.close()
    return poses, tstamps


def evo_sim3(poses, tstamps, gt_path):
    g = np.loadtxt(gt_path)  # ts(s) tx ty tz qx qy qz qw  (event-frame GT)
    EG = PoseTrajectory3D(positions_xyz=g[:, 1:4], orientations_quat_wxyz=g[:, [7, 4, 5, 6]], timestamps=g[:, 0])
    EE = PoseTrajectory3D(positions_xyz=poses[:, :3], orientations_quat_wxyz=poses[:, [6, 3, 4, 5]], timestamps=tstamps)
    gtlen = EG.get_infos()['path length (m)']
    a, b = sync.associate_trajectories(EG, EE, max_diff=0.1)
    ape = main_ape.ape(copy.deepcopy(a), copy.deepcopy(b), pose_relation=metrics.PoseRelation.translation_part,
                       align=True, correct_scale=True)
    return ape.stats['mean'] / gtlen * 100, ape.stats['rmse'] * 100, gtlen, len(b.timestamps)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--datapath', default='/data')
    p.add_argument('--scenes', nargs='+', default=['corner_slow1', 'desk_normal1', 'sofa_fast1', 'mountain_fast1'])
    p.add_argument('--network', default='/project/weights/devo.pth')
    p.add_argument('--config', default='/project/config/default.yaml')
    p.add_argument('--trials', type=int, default=1)
    p.add_argument('--outdir', default='/data/devo_out')
    p.add_argument('--opts', nargs='+', default=[])
    a = p.parse_args()
    cfg.merge_from_file(a.config)
    cfg.merge_from_list(a.opts)
    torch.manual_seed(1234)
    os.makedirs(a.outdir, exist_ok=True)
    # DEVO baseline from the DEIO paper Table IV (compare DEVO to DEVO, not to DEIO)
    paper = {'corner_slow1': 0.59, 'desk_normal1': 0.11, 'sofa_fast1': 0.38, 'mountain_fast1': 0.37}
    for s in a.scenes:
        sd = os.path.join(a.datapath, s)
        res = []
        for tr in range(a.trials):
            poses, tstamps = run_scene(sd, a.network)
            mpe, ate, gtlen, n = evo_sim3(poses, tstamps, os.path.join(sd, 'poses_evs_left.txt'))
            np.savetxt(os.path.join(a.outdir, f"{s}_trial{tr}.tum"), np.c_[tstamps, poses])
            res.append(mpe)
            print(f"RESULT {s} trial{tr}: Sim3 MPE={mpe:.3f}  ATE={ate:.2f}cm  (gtlen {gtlen:.2f}m, {n} matched)  paper={paper.get(s,'-')}")
        print(f"==> {s}: median Sim3 MPE = {np.median(res):.3f}  (paper {paper.get(s,'-')})")
