"""DEIO eval on VECtor (reconstruction). Mirrors script/eval_deio/uzh-fpv.py — the
upstream inertial template — but uses utils.load_utils.vector_evs_iterator (480x640) and
VECtor file names produced by deio/prepare_vector.py. No DEIO source is modified; this is
mounted in as script/eval_deio/vector.py. Run inside the event-world/deio container."""
import os, math
import numpy as np
import torch
import quaternion
import evo
from evo.tools.settings import SETTINGS
SETTINGS['plot_backend'] = 'Agg'

from devo.config import cfg
from utils.load_utils import load_gt_us, vector_evs_iterator
from utils.eval_utils import log_results, compute_median_results, run_DEIO2

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--inputdir', default="datasets")
    p.add_argument('--network', type=str, default='DEVO.pth')
    p.add_argument('--val_split', type=str, default="splits")
    p.add_argument('--config', default="config/vector.yaml")
    p.add_argument('--stride', type=int, default=1)
    p.add_argument('--viz', action="store_true")
    p.add_argument('--enable_event', action="store_true")
    p.add_argument('--trials', type=int, default=1)
    p.add_argument('--plot', action="store_true")
    p.add_argument('--opts', nargs='+', default=[])
    p.add_argument('--save_trajectory', action="store_true")
    p.add_argument('--side', type=str, default="left")
    p.add_argument('--resnet', action='store_true')
    p.add_argument('--block_dims', type=str, default="64,128,256")
    p.add_argument('--initial_dim', type=int, default=64)
    p.add_argument('--pretrain', type=str, default="resnet18")
    args = p.parse_args()

    cfg.merge_from_file(args.config)
    cfg.merge_from_list(args.opts)
    cfg.resnet = args.resnet
    cfg.block_dims = list(map(int, args.block_dims.split(',')))
    cfg.initial_dim = args.initial_dim
    cfg.pretrain = args.pretrain
    print(cfg, "\n")
    assert not cfg.CLASSIC_LOOP_CLOSURE
    H, W = 480, 640

    test_scenes = open(args.val_split).read().split()
    print("scenes:", test_scenes)
    dataset_name = "VECtor/EVO"
    if cfg.LOOP_CLOSURE: dataset_name += "_GBA"
    if cfg.ENALBE_IMU:   dataset_name += "_IMU"

    results_dict_scene, figures, all_results, outfolder = {}, {}, [], None
    for scene in test_scenes:
        print(f"Eval on {scene}")
        results_dict_scene[scene] = []
        groundtruth = os.path.join(args.inputdir, scene, "stamped_groundtruth_us.txt")
        imupath     = os.path.join(args.inputdir, scene, "imu.txt")
        for trial in range(args.trials):
            print(f"\nTrial {trial} of {scene}")
            datapath_val = os.path.join(args.inputdir, scene)
            tss_traj_us, traj_hf = load_gt_us(groundtruth)

            all_gt = {}
            for sod, d in zip(tss_traj_us, traj_hf):
                sod = float(sod / 1e6)
                T = np.eye(4)
                q = quaternion.from_float_array([float(d[6]), float(d[3]), float(d[4]), float(d[5])])
                T[:3, :3] = quaternion.as_rotation_matrix(q)
                T[:3, 3] = [float(d[0]), float(d[1]), float(d[2])]
                all_gt[sod] = {'T': T}
            all_gt_keys = sorted(all_gt.keys())

            t_offset_us = np.loadtxt(os.path.join(datapath_val, "t0_us.txt"))
            all_imu = np.loadtxt(imupath, delimiter=' ', usecols=range(1, 8))
            all_imu[:, 0] *= 1e6
            all_imu[:, 0] -= t_offset_us
            all_imu = all_imu[all_imu[:, 0] > 0]
            all_imu[:, 1:4] *= 180 / math.pi          # match uzh-fpv.py gyro handling
            all_imu = all_imu[all_imu[:, 0].argsort()]

            traj_est, tstamps, flowdata, _ = run_DEIO2(
                datapath_val, cfg, args.network, viz=args.viz,
                iterator=vector_evs_iterator(datapath_val, stride=args.stride, timing=False, H=H, W=W),
                _all_imu=all_imu, _all_gt=all_gt, _all_gt_keys=all_gt_keys,
                timing=False, H=H, W=W, viz_flow=False)

            data = (traj_hf, tss_traj_us, traj_est, tstamps)
            hyperparam = (None, args.network, dataset_name, scene, trial, cfg, args)
            all_results, results_dict_scene, figures, outfolder = log_results(
                data, hyperparam, all_results, results_dict_scene, figures,
                plot=True, save=True, return_figure=False, stride=args.stride,
                expname=scene, _n_to_align=-1)
        print(scene, sorted(results_dict_scene[scene]))

    results_dict = compute_median_results(results_dict_scene, all_results, dataset_name, outfolder=outfolder)
    for k in results_dict:
        print(k, results_dict[k])
    print("Done!")
