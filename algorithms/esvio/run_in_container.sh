#!/bin/bash
# In-container orchestration for one ESVIO run (headless). Mirrors volkbay's
# script/run.sh + script/record_traj.sh: roscore -> roslaunch the (headless) ESVIO
# nodes -> rosbag record the odometry -> rosbag play the sequence -> export TUM.
#
# Driven by env vars (set by run_esvio.sh):
#   LAUNCH_FILE   roslaunch file (path)
#   CONFIG_PATH   esvio.yaml config (optional; else launch default)
#   ESVIO_PATH    config directory (optional)
#   ODOM_TOPIC    estimator odometry topic to record  (/stereo_esvio_estimator/odometry)
#   OUT_DIR       output directory (also the config's output_path mount)
#   PLAY_RATE     rosbag play rate (default 1.0)
#   INIT_WAIT     seconds to wait for nodes before playback (default 10)
#   DRAIN_WAIT    seconds to wait after playback before stopping record (default 5)
# Positional args: the bag files to play (already on container paths).
set -o pipefail   # NOT -u: ROS profile scripts reference unset vars while sourcing
source /opt/ros/noetic/setup.bash
source /catkin_ws_dvs/devel/setup.bash
export MPLBACKEND=Agg
export ROS_MASTER_URI=http://localhost:11311
export ROS_HOSTNAME=localhost

: "${LAUNCH_FILE:?}"; : "${ODOM_TOPIC:?}"; : "${OUT_DIR:?}"
CONFIG_PATH="${CONFIG_PATH:-}"; ESVIO_PATH="${ESVIO_PATH:-}"
PLAY_RATE="${PLAY_RATE:-1.0}"; INIT_WAIT="${INIT_WAIT:-10}"; DRAIN_WAIT="${DRAIN_WAIT:-5}"
BAGS=("$@")
mkdir -p "$OUT_DIR"

echo ">> [1/5] roscore"
roscore >"$OUT_DIR/roscore.log" 2>&1 &
until rostopic list >/dev/null 2>&1; do sleep 0.3; done

echo ">> [2/5] roslaunch $LAUNCH_FILE"
largs=()
[ -n "$CONFIG_PATH" ] && largs+=("config_path:=$CONFIG_PATH")
[ -n "$ESVIO_PATH" ]  && largs+=("esvio_path:=$ESVIO_PATH")
roslaunch --wait "$LAUNCH_FILE" "${largs[@]}" >"$OUT_DIR/esvio_nodes.log" 2>&1 &
echo "   waiting ${INIT_WAIT}s for nodes to initialise"; sleep "$INIT_WAIT"

echo ">> [3/5] recording $ODOM_TOPIC"
rosbag record -O "$OUT_DIR/odom.bag" "$ODOM_TOPIC" __name:=odomrec >"$OUT_DIR/record.log" 2>&1 &
sleep 2

echo ">> [4/5] playing ${#BAGS[@]} bags @ ${PLAY_RATE}x"
rosbag play --clock -r "$PLAY_RATE" "${BAGS[@]}" >"$OUT_DIR/play.log" 2>&1
echo "   playback done; draining ${DRAIN_WAIT}s"; sleep "$DRAIN_WAIT"

rosnode kill /odomrec >/dev/null 2>&1 || true
sleep 2

echo ">> [5/5] exporting TUM trajectory"
cd "$OUT_DIR"
evo_traj bag odom.bag "$ODOM_TOPIC" --save_as_tum >"$OUT_DIR/evo_traj.log" 2>&1 || true
tum="$(ls -1 *odometry.tum 2>/dev/null | head -1)"
if [ -n "$tum" ]; then cp -f "$tum" stamped_traj.tum; echo "   wrote stamped_traj.tum from $tum"; else
  echo "   !! no TUM produced (no odometry recorded?)"; fi

# odometry message count (sanity)
n="$(rosbag info odom.bag 2>/dev/null | grep -m1 "$ODOM_TOPIC" || true)"
echo "   recorded: $n"

rosnode kill -a >/dev/null 2>&1 || true
pkill -f rosmaster >/dev/null 2>&1 || true
echo ">> done; outputs:"; ls -lh "$OUT_DIR"
exit 0
