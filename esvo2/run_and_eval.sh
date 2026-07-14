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
# FAST_PROFILE=1 -> the authors' fast-sequence recipe from NAIL-HNU/ESVO2 issue #9:
# events downscaled to 320x240 + generation_rate_hz 200 (halved calib, same extrinsics).
# Results land in vector-fastprofile/ to keep the released-config tier separate.
if [ "${FAST_PROFILE:-0}" = "1" ]; then
  OUT="$HERE/vector-fastprofile/$SEQ"; SUF2="_ds2"; DSARG="--downscale 2"
  LAUNCH="$HERE/launch/system_vector_fast_headless.launch"
  XMOUNTS=(-v "$HERE/calib_fast_vector":/work/calib_fast_vector:ro -v "$HERE/cfg_fast":/work/cfg_fast:ro)
else
  OUT="$HERE/vector/$SEQ"; SUF2=""; DSARG=""
  LAUNCH="$HERE/launch/system_vector_headless.launch"
  XMOUNTS=()
fi
mkdir -p "$OUT"
[ -d "$DATA" ] || { echo "ERROR: no data at $DATA"; exit 1; }

# Bag preparation — temporal repacking is done EXCLUSIVELY by upstream's own
# events_repacking_tool (EventMessageEditor, 1000 Hz, built in the image), per the
# authors' recipe. Our tooling only does a lossless type conversion
# (prophesee->dvs, native chunking; + the issue-#9 2x spatial downscale for the
# fast profile) and a byte-preserving L+R merge to feed the tool's single input.
UP="$DATA/${SEQ}_upstream1k${SUF2}.bag"
if [ ! -s "$UP" ]; then
  for side in left right; do
    src="$DATA/${SEQ}_${side}_event.bag"; nat="$DATA/${SEQ}_${side}_event_dvsnat${SUF2}.bag"
    [ -s "$src" ] || { echo "ERROR: missing $src"; exit 1; }
    if [ ! -s "$nat" ]; then
      echo ">> type-converting ${side} events (native chunking)${DSARG:+ + downscale}"
      rm -f "$nat.tmp"
      "$PY" "$ROOT/scripts/prophesee_to_dvs_bag.py" "$src" "$nat.tmp" \
            --out-topic "/davis/${side}/events" $DSARG
      mv "$nat.tmp" "$nat"
    fi
  done
  MERGED="$DATA/${SEQ}_events_in${SUF2}.bag"
  echo ">> merging L+R (byte-preserving)"
  rm -f "$MERGED"
  "$PY" "$ROOT/scripts/merge_dvs_bags.py" "$MERGED" \
        "$DATA/${SEQ}_left_event_dvsnat${SUF2}.bag" "$DATA/${SEQ}_right_event_dvsnat${SUF2}.bag"
  echo ">> repacking with UPSTREAM events_repacking_tool (1000 Hz) + IMU merge"
  rm -f "$UP.tmp"
  docker run --rm --entrypoint /bin/bash -v "$DATA":/data \
    "$IMAGE" -c "source /opt/ros/noetic/setup.bash && source /catkin_ws/devel/setup.bash && \
      /catkin_ws/devel/lib/events_repacking_tool/EventMessageEditor \
      /data/$(basename "$MERGED") /data/${SEQ}_imu.bag /data/$(basename "$UP").tmp"
  mv "$UP.tmp" "$UP"
  rm -f "$MERGED" "$DATA/${SEQ}_left_event_dvsnat${SUF2}.bag" "$DATA/${SEQ}_right_event_dvsnat${SUF2}.bag"
fi
[ -s "$UP" ] || { echo "ERROR: upstream repack failed for $UP"; exit 1; }

echo "== running ESVO2 on vector/$SEQ (headless, CPU, play rate ${PLAY_RATE:-0.25}x)"
docker run --rm --entrypoint /bin/bash \
  -v "$DATA":/data:ro \
  -v "$OUT":/out \
  -v "$LAUNCH":/work/system_vector_headless.launch:ro \
  -v "$HERE/run_in_container.sh":/work/run_in_container.sh:ro \
  "${XMOUNTS[@]}" \
  -e OUT_DIR=/out \
  -e PLAY_RATE="${PLAY_RATE:-0.25}" -e INIT_WAIT="${INIT_WAIT:-10}" -e DRAIN_WAIT="${DRAIN_WAIT:-8}" \
  "$IMAGE" /work/run_in_container.sh \
  "/data/${SEQ}_upstream1k${SUF2}.bag"

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
