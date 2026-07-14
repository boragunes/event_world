#!/usr/bin/env bash
# End-to-end ESVO2 on one VECtor sequence: run (Docker, headless, CPU) -> evaluate vs
# event-camera-frame ground truth with evo (SE3 -- stereo+IMU => metric).
# Produces esvo2/vector/<seq>/ (trajectory + metrics.json + plots + logs).
#
# Usage:  esvo2/run_and_eval.sh desk-normal
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
IMAGE="${IMAGE:-event-world/esvo2:latest}"
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

# events: lossless prophesee->dvs conversion, repacked at 1 kHz chunks (cached).
# The ESVO family needs fine-grained event-array chunking: the TS/AA node samples
# "events received so far" on a 100 Hz clock, so 60 Hz chunks starve each tick of up
# to ~17 ms of fresh events (desk-normal diverged 400 m); 1 kHz matches what upstream's
# own events_repacking_tool produces for their repacked bags.
for side in left right; do
  src="$DATA/${SEQ}_${side}_event.bag"; dvs="$DATA/${SEQ}_${side}_event_dvs1k.bag"
  [ -s "$src" ] || { echo "ERROR: missing $src"; exit 1; }
  if [ ! -s "$dvs" ]; then
    echo ">> converting ${side} events -> dvs_msgs @1kHz"
    rm -f "$dvs.tmp"
    "$PY" "$ROOT/scripts/prophesee_to_dvs_bag.py" "$src" "$dvs.tmp" \
          --out-topic "/davis/${side}/events" --repack-hz 1000
    mv "$dvs.tmp" "$dvs"
  fi
  [ -s "$dvs" ] || { echo "ERROR: conversion failed for $dvs"; exit 1; }
done

echo "== running ESVO2 on vector/$SEQ (headless, CPU, play rate ${PLAY_RATE:-0.25}x)"
docker run --rm --entrypoint /bin/bash \
  -v "$DATA":/data:ro \
  -v "$OUT":/out \
  -v "$HERE/launch/system_vector_headless.launch":/work/system_vector_headless.launch:ro \
  -v "$HERE/run_in_container.sh":/work/run_in_container.sh:ro \
  -e OUT_DIR=/out \
  -e PLAY_RATE="${PLAY_RATE:-0.25}" -e INIT_WAIT="${INIT_WAIT:-10}" -e DRAIN_WAIT="${DRAIN_WAIT:-8}" \
  "$IMAGE" /work/run_in_container.sh \
  "/data/${SEQ}_left_event_dvs1k.bag" "/data/${SEQ}_right_event_dvs1k.bag" "/data/${SEQ}_imu.bag"

# trajectory: prefer the node's own file; fall back to the recorded pose topic
if [ -s "$OUT/stamped_traj_estimate.txt" ]; then
  cp -f "$OUT/stamped_traj_estimate.txt" "$OUT/stamped_traj.tum"
  echo ">> using node-saved stamped_traj_estimate.txt ($(grep -vc '^#' "$OUT/stamped_traj.tum") poses)"
elif [ -s "$OUT/pose.bag" ]; then
  echo ">> node file missing; exporting recorded pose topic"
  ( cd "$OUT" && "$PY" -m evo.main_traj bag pose.bag /esvo2_tracking/pose_pub --save_as_tum >/dev/null 2>&1 || \
    "$HOME/.venvs/evtools/bin/evo_traj" bag pose.bag /esvo2_tracking/pose_pub --save_as_tum >/dev/null 2>&1 )
  f="$(ls -1 "$OUT"/*pose_pub.tum 2>/dev/null | head -1)"
  [ -n "$f" ] && cp -f "$f" "$OUT/stamped_traj.tum"
fi
[ -s "$OUT/stamped_traj.tum" ] || { echo "ERROR: no trajectory produced"; exit 1; }

# evaluate vs the EXACT event-camera-frame GT (left event cam), SE3 (metric)
SCENE="$(echo "$SEQ" | tr '-' '_')1"
GT="$ROOT/data/deio_vector/$SCENE/poses_evs_left.txt"
[ -s "$GT" ] || { echo "ERROR: no event-frame GT at $GT"; exit 1; }
echo "== evaluating vector/$SEQ (SE3, event-frame GT)"
"$PY" "$ROOT/scripts/evaluate.py" --algo esvo2 \
      --est "$OUT/stamped_traj.tum" --gt "$GT" \
      --out-dir "$OUT" --label "esvo2/vector/$SEQ" --align se3
cp -f "$GT" "$OUT/${SEQ}_gt.txt"
