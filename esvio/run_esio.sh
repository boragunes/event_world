#!/usr/bin/env bash
# Run ESIO (ESVIO's event-only variant: stereo events + IMU, NO images) on one
# VECtor sequence, headless, and capture the estimated trajectory as TUM
# (esvio/<dataset>-esio/<seq>/stamped_traj.tum).
#
# Same upstream container/binaries as ESVIO (event-world/esvio:latest); the only
# differences vs run_esvio.sh are: the ESIO launch (stereo_event_tracker +
# stereo_esio_estimator, no image tracker), the ESIO odometry topic, and that we
# do NOT play the stereo camera bags (event-only). The authors do not report ESIO
# on VECtor (their Table II is ESVIO only), so this is new coverage.
#
# Usage:
#   run_esio.sh <dataset> <sequence>          # dataset must be 'vector' for now
#   sg docker -c "esvio/run_esio.sh vector desk-normal"
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
IMAGE="${IMAGE:-event-world/esvio:latest}"
PY="${PY:-$HOME/.venvs/evtools/bin/python}"

DATASET="${1:?usage: run_esio.sh <dataset> <sequence>}"
SEQ="${2:?usage: run_esio.sh <dataset> <sequence>}"

DATA="$ROOT/data/$DATASET/$SEQ"
OUT="$HERE/${DATASET}-esio/$SEQ"
mkdir -p "$OUT"
[ -d "$DATA" ] || { echo "ERROR: no data at $DATA (run the dataset download script first)"; exit 1; }

case "$DATASET" in
  vector)
    CONFIG_DIR="esvio_VECtor_small_scale"
    # Same VECtor IMU-noise model as run_esvio.sh (ESIO uses the same IMU); upstream
    # acc_n:0.2 over-trusts the accelerometer and inflates scale on low-excitation seqs.
    : "${CONFIG_OVERRIDES:=acc_n:0.08 gyr_n:0.004 acc_w:0.00004 gyr_w:2.0e-6}"
    # VECtor events are prophesee_event_msgs; convert to dvs_msgs @60Hz (lossless; cached,
    # shared with run_esvio.sh so already present if ESVIO was run on this seq).
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
    # ESIO = event-only: play ONLY the stereo event bags + IMU (no camera bags).
    BAGS=( "${SEQ}_left_event_dvs.bag" "${SEQ}_right_event_dvs.bag" "${SEQ}_imu.bag" )
    ;;
  *)
    echo "ERROR: dataset '$DATASET' not supported yet"; exit 1 ;;
esac

CFG="/catkin_ws_dvs/src/ESVIO/config/${CONFIG_DIR}/esvio.yaml"
CFGDIR="/catkin_ws_dvs/src/ESVIO/config/${CONFIG_DIR}/"
ODOM="/stereo_esio_estimator/odometry"

# host bag paths -> container /data/<name>
cbags=(); for b in "${BAGS[@]}"; do
  [ -s "$DATA/$b" ] || { echo "ERROR: missing bag $DATA/$b"; exit 1; }
  cbags+=( "/data/$b" )
done

echo ">> running ESIO (event-only) on $DATASET/$SEQ (headless)"
docker run --rm \
  -v "$DATA":/data:ro \
  -v "$OUT":/home/cpy/Datasets/output \
  -v "$HERE/launch/esio_VECtor_headless.launch":/work/esio_headless.launch:ro \
  -v "$HERE/run_in_container.sh":/work/run_in_container.sh:ro \
  -e LAUNCH_FILE=/work/esio_headless.launch \
  -e CONFIG_PATH="$CFG" -e ESVIO_PATH="$CFGDIR" \
  -e ODOM_TOPIC="$ODOM" -e OUT_DIR=/home/cpy/Datasets/output \
  -e INIT_WAIT="${INIT_WAIT:-10}" -e PLAY_RATE="${PLAY_RATE:-1.0}" \
  -e FIX_CALIB="${FIX_CALIB:-1}" -e CONFIG_OVERRIDES="${CONFIG_OVERRIDES:-}" \
  -e PLAY_START="${PLAY_START:-0}" \
  "$IMAGE" /work/run_in_container.sh "${cbags[@]}"

echo ">> ESIO run complete. Trajectory: $OUT/stamped_traj.tum"
ls -lh "$OUT" 2>/dev/null || true
