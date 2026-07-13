#!/usr/bin/env bash
# End-to-end SDEVO on one VECtor sequence: run (Docker, headless) -> evaluate vs
# event-camera-frame ground truth with evo (SE3 -- SDEVO is stereo => metric).
# Produces sdevo/vector/<seq>/ (trajectory + metrics.json + plots + logs).
#
# Usage:  sdevo/run_and_eval.sh desk-normal
#         sg docker -c "sdevo/run_and_eval.sh desk-normal"   # if shell lacks docker group
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
IMAGE="${IMAGE:-event-world/sdevo:latest}"
PY="${PY:-$HOME/.venvs/evtools/bin/python}"
SEQ="${1:?usage: run_and_eval.sh <sequence>  (e.g. desk-normal)}"

# re-exec under the docker group if this shell lacks docker access
if ! docker info >/dev/null 2>&1; then
  exec sg docker -c "bash '${BASH_SOURCE[0]}' '$SEQ'"
fi

DATA="$ROOT/data/vector/$SEQ"
OUT="$HERE/vector/$SEQ"
mkdir -p "$OUT"
[ -d "$DATA" ] || { echo "ERROR: no data at $DATA"; exit 1; }

# VECtor events are prophesee msgs; SDEVO's image_representation subscribes
# dvs_msgs on /davis/{left,right}/events -- same conversion as ESVIO (cached).
for side in left right; do
  src="$DATA/${SEQ}_${side}_event.bag"; dvs="$DATA/${SEQ}_${side}_event_dvs.bag"
  [ -s "$src" ] || { echo "ERROR: missing $src"; exit 1; }
  if [ ! -s "$dvs" ]; then
    echo ">> converting ${side} events -> dvs_msgs"
    "$PY" "$ROOT/scripts/prophesee_to_dvs_bag.py" "$src" "$dvs" \
          --out-topic "/davis/${side}/events" --repack-hz 60
  fi
done

echo "== running SDEVO on vector/$SEQ (headless, play rate ${PLAY_RATE:-0.2}x)"
docker run --rm --gpus all --ipc=host --entrypoint /bin/bash \
  -v "$DATA":/data:ro \
  -v "$OUT":/catkin_ws/src/SDEVO/DEVO/output \
  -v "$HERE/launch/voxel_vector_nodes.launch":/work/voxel_vector_nodes.launch:ro \
  -v "$HERE/sdevo_spin.py":/work/sdevo_spin.py:ro \
  -v "$HERE/run_in_container.sh":/work/run_in_container.sh:ro \
  -e OUT_DIR=/catkin_ws/src/SDEVO/DEVO/output \
  -e PLAY_RATE="${PLAY_RATE:-0.2}" -e TIMER_HZ="${TIMER_HZ:-2}" \
  -e INIT_WAIT="${INIT_WAIT:-25}" -e DRAIN_WAIT="${DRAIN_WAIT:-20}" \
  "$IMAGE" /work/run_in_container.sh \
  "/data/${SEQ}_left_event_dvs.bag" "/data/${SEQ}_right_event_dvs.bag"

# evaluate vs the EXACT event-camera-frame GT (left event cam), SE3 (metric)
SCENE="$(echo "$SEQ" | tr '-' '_')1"      # desk-normal -> desk_normal1
GT="$ROOT/data/deio_vector/$SCENE/poses_evs_left.txt"
[ -s "$GT" ] || { echo "ERROR: no event-frame GT at $GT"; exit 1; }
echo "== evaluating vector/$SEQ (SE3, event-frame GT)"
"$PY" "$ROOT/scripts/evaluate.py" --algo sdevo \
      --est "$OUT/stamped_traj.tum" --gt "$GT" \
      --out-dir "$OUT" --label "sdevo/vector/$SEQ" --align se3
cp -f "$GT" "$OUT/${SEQ}_gt.txt"
