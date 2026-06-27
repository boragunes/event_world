#!/usr/bin/env bash
# Build the faithful DEIO image (event-world/deio:latest).
# Long build (~30-60 min): conda env (PyTorch 2.3.1 + cu118) + DPVO/DEVO CUDA
# extensions + GTSAM Python bindings. Needs the NVIDIA Container Toolkit only at run
# time, not build time. Invoke with docker access, e.g.:
#   sg docker -c "deio/build.sh"
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${IMAGE:-event-world/deio:latest}"
echo ">> building $IMAGE (faithful DEIO @ pinned commit)"
docker build -t "$IMAGE" "$HERE"
echo ">> done: $IMAGE"
