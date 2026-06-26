#!/usr/bin/env bash
# Run ESVIO on one dataset sequence, headless, and capture the estimated
# trajectory as TUM (results/esvio/<dataset>/<seq>/stamped_traj.tum).
#
# Usage:
#   run_esvio.sh <dataset> <sequence>
#   run_esvio.sh vector desk-normal
#
# Notes:
#  * Needs the Docker image (algorithms/esvio/build.sh) and the sequence bags
#    (datasets/<dataset>/download_*.sh).
#  * Invoke with docker access, e.g.:  sg docker -c "algorithms/esvio/run_esvio.sh vector desk-normal"
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
IMAGE="${IMAGE:-event-world/esvio:latest}"
PY="${PY:-$HOME/.venvs/evtools/bin/python}"

DATASET="${1:?usage: run_esvio.sh <dataset> <sequence>}"
SEQ="${2:?usage: run_esvio.sh <dataset> <sequence>}"

DATA="$ROOT/data/$DATASET/$SEQ"
OUT="$ROOT/results/esvio/$DATASET/$SEQ"
mkdir -p "$OUT"
[ -d "$DATA" ] || { echo "ERROR: no data at $DATA (run the dataset download script first)"; exit 1; }

case "$DATASET" in
  vector)
    CONFIG_DIR="esvio_VECtor_small_scale"
    # VECtor events are prophesee_event_msgs at ~3.9 kHz tiny arrays; convert to
    # dvs_msgs and repack to 60 Hz (what ESVIO expects). Lossless; cached.
    for side in left right; do
      src="$DATA/${SEQ}_${side}_event.bag"
      dvs="$DATA/${SEQ}_${side}_event_dvs.bag"
      [ -s "$src" ] || { echo "ERROR: missing $src"; exit 1; }
      if [ ! -s "$dvs" ]; then
        echo ">> converting ${side} events -> dvs_msgs @60Hz"
        "$PY" "$ROOT/scripts/prophesee_to_dvs_bag.py" "$src" "$dvs" \
              --out-topic "/davis/${side}/events" --repack-hz 60
      fi
    done
    BAGS=( "${SEQ}_left_event_dvs.bag" "${SEQ}_right_event_dvs.bag" "${SEQ}_imu.bag"
           "${SEQ}_left_camera.bag" "${SEQ}_right_camera.bag" )
    ;;
  *)
    echo "ERROR: dataset '$DATASET' not supported yet"; exit 1 ;;
esac

CFG="/catkin_ws_dvs/src/ESVIO/config/${CONFIG_DIR}/esvio.yaml"
CFGDIR="/catkin_ws_dvs/src/ESVIO/config/${CONFIG_DIR}/"
ODOM="/stereo_esvio_estimator/odometry"

# host bag paths -> container /data/<name>
cbags=(); for b in "${BAGS[@]}"; do
  [ -s "$DATA/$b" ] || { echo "ERROR: missing bag $DATA/$b"; exit 1; }
  cbags+=( "/data/$b" )
done

echo ">> running ESVIO on $DATASET/$SEQ (headless)"
docker run --rm \
  -v "$DATA":/data:ro \
  -v "$OUT":/home/cpy/Datasets/output \
  -v "$HERE/launch/esvio_VECtor_small_scale_headless.launch":/work/esvio_headless.launch:ro \
  -v "$HERE/run_in_container.sh":/work/run_in_container.sh:ro \
  -e LAUNCH_FILE=/work/esvio_headless.launch \
  -e CONFIG_PATH="$CFG" -e ESVIO_PATH="$CFGDIR" \
  -e ODOM_TOPIC="$ODOM" -e OUT_DIR=/home/cpy/Datasets/output \
  -e INIT_WAIT="${INIT_WAIT:-10}" -e PLAY_RATE="${PLAY_RATE:-1.0}" \
  "$IMAGE" /work/run_in_container.sh "${cbags[@]}"

echo ">> ESVIO run complete. Trajectory: $OUT/stamped_traj.tum"
ls -lh "$OUT" 2>/dev/null || true
