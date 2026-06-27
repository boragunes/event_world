# event_world — an open benchmark for event-camera SLAM

Reproducible, containerized evaluation of open-source **event-camera SLAM / VIO**
algorithms on standard datasets, with results cross-checked against the numbers
reported in each method's own paper.

What makes this different: we publish the **Dockerfiles**, the **test-running
scripts**, and the **estimated trajectories** — not just a table of numbers.

## Principles

1. **Faithful containers.** Each algorithm runs from a Docker image that stays as
   close as possible to its upstream repository (we pin commits; we do not patch
   the algorithm).
2. **Minimal preprocessing.** Datasets are fed to the algorithms in their original
   distribution form (e.g. ROS bags), with at most topic remaps at playback time.
3. **Transparent evaluation.** Estimated trajectories are compared to ground truth
   with [`evo`](https://github.com/MichaelGrupp/evo) (ATE / RPE), and we also report
   each paper's own metric (e.g. MPE % / MRE) for an apples-to-apples comparison.

## Status

| Algorithm | Modality | Datasets | State |
|-----------|----------|----------|-------|
| [ESVIO](esvio/) | stereo events + IMU (+ frames) | VECtor small-scale — [report](docs/validation/esvio_vector.md) | 8/11 good (6 beat paper); 2 fast seqs fail init |
| DEIO, ESVO2, SuperEvent, … | — | DSEC, M3ED, … | planned |

## Layout

```
<algo>/              the algorithm: Dockerfile + build/run scripts (faithful to upstream)
  <ds>/<seq>/        committed per sequence: estimated trajectory (stamped_traj.tum),
                     ground truth (<seq>_gt.txt), metrics.json, PDF + PNG plots
datasets/<ds>/       download scripts (raw data is NOT committed)
scripts/             shared evaluation (evo) + event-format conversion
docs/validation/     our numbers vs each paper
data/                raw datasets (gitignored, fetched locally)
```

So `esvio/` holds the container + run scripts *and* `esvio/vector/<seq>/` with the
estimated trajectory, ground truth, and plots for each sequence. A second algorithm
would be a sibling `deio/` with its own `deio/<ds>/<seq>/` results.

## Quickstart (ESVIO on VECtor)

```bash
# 0. Docker (one-time, needs sudo):
sudo apt-get install -y docker.io && sudo usermod -aG docker "$USER"   # then re-login

# 1. Build the ESVIO image (faithful to volkbay/ESVIO @ pinned commit)
esvio/build.sh

# 2. Fetch a small VECtor sequence (ROS bags + TUM ground truth)
datasets/vector/download_vector.sh desk-normal

# 3. Run + evaluate end-to-end  ->  esvio/vector/desk-normal/
esvio/run_and_eval.sh vector desk-normal
```

## Attribution

Each algorithm and dataset is the work of its original authors and retains its
own license (ESVIO is GPLv3). This repository only adds containerization, run
scripts, and evaluation glue. See each `<algo>/README.md` for sources.
