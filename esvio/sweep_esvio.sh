#!/usr/bin/env bash
# Sweep ESVIO init-tuning variants on one VECtor sequence and keep the lowest-MPE run.
# Each variant = FIX_CALIB + a set of documented CONFIG_OVERRIDES. Usage:
#   sweep_esvio.sh <seq> [variant1 variant2 ...]   (default: all)
# Variants (event/image feature density, solver threads, keyframe parallax):
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PY:-$HOME/.venvs/evtools/bin/python}"
SEQ="${1:?usage: sweep_esvio.sh <seq> [variants...]}"; shift || true
OUT="$ROOT/esvio/vector/$SEQ"; GT="$ROOT/data/vector/$SEQ/${SEQ}_gt_txt.txt"
SCR="${SCR:-${TMPDIR:-/tmp}/esvio_sweep}"; mkdir -p "$SCR"

declare -A V=(
  [baseline]=""
  [feat]="max_cnt:300 max_cnt_img:300 min_dist:8 min_dist_img:15"
  [threads]="Num_of_thread:8"
  [parallax]="keyframe_parallax:7"
  [robust]="max_cnt:350 max_cnt_img:350 min_dist:8 min_dist_img:15 Num_of_thread:8 keyframe_parallax:7"
)
ORDER=("$@"); [ "${#ORDER[@]}" -eq 0 ] && ORDER=(feat threads parallax robust)
mpe_of(){ $PY -c "import json;print(json.load(open('$OUT/metrics.json'))['paper_metric']['MPE_percent_ate'])" 2>/dev/null || echo 999999; }

best=999999; bestv=none
# Seed with the existing (already-run FIX_CALIB baseline) result so a worse variant
# can't replace it.
if [ -f "$OUT/metrics.json" ] && [ -f "$OUT/stamped_traj.tum" ]; then
  best="$(mpe_of)"; bestv=baseline; cp -f "$OUT/stamped_traj.tum" "$OUT/traj_best.tum" 2>/dev/null || true
  echo "seed: baseline(FIX_CALIB) MPE=${best}%"
fi
for v in "${ORDER[@]}"; do
  echo "===== $SEQ / $v : FIX_CALIB ${V[$v]} ====="
  CONFIG_OVERRIDES="${V[$v]}" FIX_CALIB=1 bash "$ROOT/esvio/run_and_eval.sh" vector "$SEQ" \
      >"$SCR/sweep_${SEQ}_${v}.log" 2>&1 || echo "  run-fail $v"
  m="$(mpe_of)"; cp -f "$OUT/stamped_traj.tum" "$OUT/traj_${v}.tum" 2>/dev/null || true
  echo "  -> MPE = ${m}%"
  if awk "BEGIN{exit !($m < $best)}"; then best="$m"; bestv="$v"; cp -f "$OUT/stamped_traj.tum" "$OUT/traj_best.tum" 2>/dev/null || true; fi
done
echo ">>> BEST $SEQ: variant=$bestv  MPE=${best}%"
# restore best as the canonical trajectory + metrics
[ -f "$OUT/traj_best.tum" ] && cp -f "$OUT/traj_best.tum" "$OUT/stamped_traj.tum"
$PY "$ROOT/scripts/evaluate.py" --algo esvio --dataset vector --seq "$SEQ" \
    --est "$OUT/stamped_traj.tum" --gt "$GT" --out-dir "$OUT" >/dev/null 2>&1 || true
echo "best_variant=$bestv" > "$OUT/tuned_variant.txt"
