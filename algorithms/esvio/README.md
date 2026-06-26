# ESVIO (Event-based Stereo Visual-Inertial Odometry)

Containerized, reproducible setup for **ESVIO** — the first stereo event-based
visual-inertial odometry (Chen, Guan, Lu; RAL2023 + IROS2023;
[arXiv:2212.13184](https://arxiv.org/abs/2212.13184)).

- Variants: **ESIO** (stereo events + IMU) and **ESVIO** (stereo events + image + IMU).
- Backend: sliding-window optimization (Ceres), ROS Noetic. **CPU-only** — no GPU needed.

## Provenance & faithfulness

| | |
|---|---|
| Original | https://github.com/arclab-hku/ESVIO |
| Docker fork used | https://github.com/volkbay/ESVIO (branch `master`) |
| Pinned commit | `16cb14a7122d216002132aa8fb58ba374f4f34de` |

The [`Dockerfile`](./Dockerfile) is the upstream volkbay Dockerfile **unchanged**,
with a single deviation: the cloned source is **pinned to the commit above** for
reproducibility. No algorithm or source-code edits are made in the image. The
HDF5→rosbag tooling baked into the image is upstream's and is only used for HDF5
datasets (DSEC/M3ED), not for VECtor/MVSEC.

## Build

```bash
./build.sh            # -> event-world/esvio:latest  (compiles Ceres 1.14 + ESVIO, ~20–40 min)
```

## Run (headless)

See [`run_esvio.sh`](./run_esvio.sh). It runs a single dataset sequence inside the
container with a virtual X display (`xvfb`), so the upstream launch files (which
start rviz) work without a desktop, and captures the estimated trajectory in
TUM format for evaluation with [`evo`](https://github.com/MichaelGrupp/evo).

Config/launch files are upstream's, selected per dataset, e.g.
`esvio_VECtor_small_scale.launch` + `config/esvio_VECtor_small_scale/esvio.yaml`.
The container's hardcoded `output_path` (`/home/cpy/Datasets/output`) is satisfied
by bind-mounting our results directory there, so the upstream YAML is never edited.
