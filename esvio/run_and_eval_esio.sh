#!/usr/bin/env bash
# End-to-end for the ESIO (event-only) variant on one VECtor sequence:
#   run ESIO (Docker, headless) -> evaluate vs ground truth with evo (SE3, metric).
# Produces esvio/vector-esio/<seq>/ with the estimated trajectory, GT, metrics.json,
# and plots. Parallels run_and_eval.sh but for the event-only ESIO variant.
#
# Usage:  esvio/run_and_eval_esio.sh <sequence>        (dataset is VECtor)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PY:-$HOME/.venvs/evtools/bin/python}"
SEQ="${1:?usage: run_and_eval_esio.sh <sequence>}"
DATASET=vector

# 1. run ESIO (use sg docker if the current shell lacks docker-group access)
echo "== running ESIO (event-only) on $DATASET/$SEQ"
if docker info >/dev/null 2>&1; then
  "$ROOT/esvio/run_esio.sh" "$DATASET" "$SEQ"
else
  sg docker -c "bash '$ROOT/esvio/run_esio.sh' '$DATASET' '$SEQ'"
fi

# 2. evaluate vs ground truth (SE3; ESIO is event+IMU => metric)
OUT="$ROOT/esvio/${DATASET}-esio/$SEQ"
GT="$ROOT/data/$DATASET/$SEQ/${SEQ}_gt_txt.txt"
echo "== evaluating $DATASET/$SEQ"
"$PY" "$ROOT/scripts/evaluate.py" --est "$OUT/stamped_traj.tum" --gt "$GT" \
      --out-dir "$OUT" --label "esio/$DATASET/$SEQ" --align se3

# (GT is not duplicated here — the identical VECtor GT is already committed under
#  esvio/vector/<seq>/<seq>_gt.txt and lives in data/vector/<seq>/.)
