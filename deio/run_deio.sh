#!/usr/bin/env bash
# Run DEIO in the faithful container on a dataset it supports out-of-the-box
# (uzh-fpv = event+IMU, the README's inertial example; or davis240c). GPU required.
# Outputs TUM trajectories to deio/<dataset>/.
#
# Needs: the image (deio/build.sh), the DEVO.pth weights, and the dataset laid out as
# DEIO's loader expects. Example:
#   DEVO_WEIGHTS=/data/DEVO.pth DATA=/data/UZH-FPV deio/run_deio.sh uzhfpv
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${IMAGE:-event-world/deio:latest}"
DATASET="${1:-uzhfpv}"
DATA="${DATA:?set DATA=/path/to/dataset (DEIO loader layout)}"
WEIGHTS="${DEVO_WEIGHTS:?set DEVO_WEIGHTS=/path/to/DEVO.pth}"

case "$DATASET" in
  uzhfpv)    SCRIPT=script/eval_deio/uzh-fpv.py;   CONFIG=config/uzhfpv.yaml;    SPLIT=script/splits/fpv/fpv_val.txt ;;
  davis240c) SCRIPT=script/eval_deio/davis240c.py; CONFIG=config/davis240c.yaml; SPLIT=script/splits/davis240c/davis240c_val.txt ;;
  *) echo "ERROR: DEIO ships runnable scripts only for uzhfpv, davis240c (got '$DATASET')"; exit 1 ;;
esac

OUT="$HERE/$DATASET"; mkdir -p "$OUT"
echo ">> DEIO $DATASET (GPU): $SCRIPT"
docker run --rm --gpus all \
  -v "$DATA":/data:ro -v "$WEIGHTS":/weights/DEVO.pth:ro -v "$OUT":/opt/DEIO/results \
  "$IMAGE" conda run --no-capture-output -n DEIO bash -lc \
    "cd /opt/DEIO && CUDA_VISIBLE_DEVICES=0 PYTHONPATH=/opt/DEIO python $SCRIPT \
       --inputdir=/data --config=$CONFIG --val_split=$SPLIT --enable_event \
       --network=/weights/DEVO.pth --save_trajectory --plot --trials=5"
echo ">> done -> $OUT (evaluate with scripts/evaluate.py against the dataset GT)"
