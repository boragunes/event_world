#!/usr/bin/env bash
# Build the base-DEVO (dpvo-clean) image. No GPU needed to build; running needs --gpus.
set -e
cd "$(dirname "$0")"
docker build -t event-world/devo:latest .
echo "Built event-world/devo:latest."
echo "Place the event checkpoint at devo/weights/devo.pth (from shadymeowy/dpvo-clean, weights/devo.pth)."
