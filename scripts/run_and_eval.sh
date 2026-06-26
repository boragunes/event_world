#!/usr/bin/env bash
# End-to-end: download (if needed) -> run ESVIO (Docker, headless) -> evaluate vs
# ground truth with evo. Produces results/esvio/<dataset>/<seq>/ with the estimated
# trajectory, metrics.json, and plots.
#
# Usage:
#   scripts/run_and_eval.sh vector desk-normal
#
# Requires: Docker (see algorithms/esvio/build.sh) and the evo venv
# (PY env var, default ~/.venvs/evtools/bin/python).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PY:-$HOME/.venvs/evtools/bin/python}"
DATASET="${1:?usage: run_and_eval.sh <dataset> <sequence>}"
SEQ="${2:?usage: run_and_eval.sh <dataset> <sequence>}"

# 1. download (if missing)
if [ ! -d "$ROOT/data/$DATASET/$SEQ" ]; then
  echo "== downloading $DATASET/$SEQ"
  "$ROOT/datasets/$DATASET/download_${DATASET}.sh" "$SEQ"
fi

# 2. run ESVIO (use sg docker if the current shell lacks docker-group access)
echo "== running ESVIO on $DATASET/$SEQ"
if docker info >/dev/null 2>&1; then
  "$ROOT/algorithms/esvio/run_esvio.sh" "$DATASET" "$SEQ"
else
  sg docker -c "bash '$ROOT/algorithms/esvio/run_esvio.sh' '$DATASET' '$SEQ'"
fi

# 3. evaluate vs ground truth
echo "== evaluating $DATASET/$SEQ"
"$PY" "$ROOT/scripts/evaluate.py" --dataset "$DATASET" --seq "$SEQ"
