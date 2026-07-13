# SDEVO — Deep Visual Odometry for Stereo Event Cameras — container + results

[SDEVO](https://github.com/NAIL-HNU/SDEVO) (Zhong, Niu, Zhou; RA-L 2025,
[arXiv:2509.08235](https://arxiv.org/abs/2509.08235)) is **deep stereo event-only VO**: DEVO's learned
patch tracking + static stereo association in the BA → **metric scale without an IMU**. It fills the
missing cell in our modality matrix (classical stereo: ESVIO/ESIO; deep mono: DEVO/DEIO; **deep
stereo: SDEVO**), and it is the paper that independently confirmed our DEIO metric-scale finding.

## Architecture (hybrid, run online)
- **C++ ROS node** `image_representation` (ESVO2 lineage): builds 5-bin L/R event voxels live from a
  rosbag, triggered by a `/sync` timer; publishes `sdevo_msgs/TimedFloat32MultiArray`.
- **Python ROS node** `sdevo.py`: the stereo DEVO fork; consumes the voxel pairs, runs the SLAM,
  auto-saves the trajectory 5 s (wall) after the last voxel.
- Weights = the **original TUM `DEVO.pth`** (md5 `3d807b8c…`, ships in the repo) — the stereo novelty
  is algorithmic, not retrained.

## Faithful container — documented deviations (no upstream code modified)
1. **The core `devo/devo.py` ships without source — we run the authors' released *bytecode*
   exactly.** The upstream git tree contains only two build artifacts of the stereo tracking
   class: the egg in `dist/` (py source, built 15:32) and a cp310 bytecode in `devo/__pycache__/`
   (15:53, **newer**). They differ materially: the egg's `update_depth()` is broken
   (`NameError: min_depth` — the egg cannot run at all) and its `block_matching()` (the core
   stereo association) diverges from the bytecode. Rather than patch or reconstruct source, the
   Dockerfile installs the newest artifact as a **sourceless module** (`devo/devo.pyc`) — zero
   reconstruction, byte-exact execution of what the authors released.
2. **Python 3.10 venv with upstream's own pins** (`torch 1.12.0+cu113`, `torchvision 0.13.0`,
   `torch-scatter 2.1.0`, `numpy 1.26.4`, `scipy 1.15.3`, `opencv 4.6.0.66`, … per their
   `environment.yml`; py3.10 is also required to execute the cp310 bytecode). Because `sdevo.py`
   imports ROS `tf`/`tf2_ros` whose stock Noetic binding (`tf2_py`) is cp38-only, we compile
   `ros/geometry`+`geometry2` against py3.10 in an overlay workspace (`/tf_ws`). (Upstream's own
   conda-py3.10 setup has the same incompatibility, unaddressed in their README.)
3. **Deterministic headless start order** ([launch/voxel_vector_nodes.launch](launch/voxel_vector_nodes.launch) +
   [sdevo_spin.py](sdevo_spin.py)): upstream's `voxel_vector.launch` starts everything at once and
   relies on a race — `sdevo.py`'s `__main__` sets `/use_sim_time` false *sometime* during startup, and
   never calls its own `run()` (= `rospy.spin()`). We start the voxel nodes first (they latch sim time
   for voxel stamping), then the upstream `VoxelListener` via a wrapper that replicates upstream's
   `__main__` and calls the upstream `run()`, then the `/sync` timer (deterministically wall-clock,
   2 Hz), then `rosbag play --clock -r 0.2`. **2 Hz wall ÷ 0.2× playback = the shipped
   `generation_rate_hz: 10`** — exactly the upstream README's formula; the 5× slowdown removes
   real-time machine-dependence.

`catkin build` (not `catkin_make`) is required — the ethz-asl dep shims build their libs as external
projects. Exact dependency commits recorded at build time in `/catkin_ws/PINNED_COMMITS.txt`.

## Run on VECtor
VECtor is a first-class citizen upstream (`voxel_vector.launch` + `calib/vector/` ship in-repo).
Input topics `/davis/{left,right}/events` (dvs_msgs) = exactly our converted VECtor bags (shared with
ESVIO; conversion is lossless and cached). **Stereo → metric → SE(3) evaluation**, against the exact
**event-camera-frame GT** (`poses_evs_left`, from VECtor's official extrinsics — see the DEVO/DEIO
work).

```bash
sdevo/build.sh                    # -> event-world/sdevo:latest
sdevo/run_and_eval.sh desk-normal # run + SE3 eval -> sdevo/vector/desk-normal/
```

## Layout
```
sdevo/
  Dockerfile  build.sh  run_and_eval.sh  run_in_container.sh
  launch/voxel_vector_nodes.launch   headless launch (upstream nodes/params, see deviations)
  sdevo_spin.py                      upstream VoxelListener entry point (calls upstream run())
  vector/<seq>/                      our runs: trajectory + GT + SE3 metrics + plots + logs
```
SDEVO, DEVO and DPVO are their original authors' work under their own licenses; this folder adds
containerization, the deterministic headless harness, and evaluation glue.
