#!/bin/bash
# In-container orchestration for one SDEVO run on VECtor (headless, deterministic).
# Mirrors the upstream README recipe (roslaunch voxel_vector.launch + rosbag play --clock)
# with a deterministic start order (see launch/voxel_vector_nodes.launch header).
#
# Env vars:
#   OUT_DIR     output dir (bind-mounted over /catkin_ws/src/SDEVO/DEVO/output)
#   PLAY_RATE   rosbag playback rate      (default 0.2  -> global_timer 2 Hz wall
#               gives the shipped generation_rate_hz=10 per the upstream formula)
#   TIMER_HZ    /sync publish rate, wall  (default 2)
#   INIT_WAIT   seconds to wait for DEVO net init before playback (default 25)
#   DRAIN_WAIT  wall seconds after playback before collecting (default 20; upstream
#               auto-saves the trajectory 5 s (wall) after the last voxel)
# Positional args: the bag files to play (container paths).
set -o pipefail
source /opt/ros/noetic/setup.bash
source /catkin_ws/devel/setup.bash
source /tf_ws/devel/setup.bash   # py3.10 tf2 bindings overlay (shadows the cp38 ones)
export PATH="/opt/venv/bin:$PATH"
export ROS_MASTER_URI=http://localhost:11311 ROS_HOSTNAME=localhost

: "${OUT_DIR:?}"
PLAY_RATE="${PLAY_RATE:-0.2}"; TIMER_HZ="${TIMER_HZ:-2}"
INIT_WAIT="${INIT_WAIT:-25}"; DRAIN_WAIT="${DRAIN_WAIT:-20}"
BAGS=("$@")
mkdir -p "$OUT_DIR"

echo ">> [1/6] roscore"
roscore >"$OUT_DIR/roscore.log" 2>&1 &
until rostopic list >/dev/null 2>&1; do sleep 0.3; done

echo ">> [2/6] voxel nodes (image_representation L/R)"
roslaunch --wait /work/voxel_vector_nodes.launch >"$OUT_DIR/voxel_nodes.log" 2>&1 &
sleep 5

echo ">> [3/6] sdevo node (upstream VoxelListener via spin wrapper; sets /use_sim_time false)"
python3 -u /work/sdevo_spin.py >"$OUT_DIR/sdevo.log" 2>&1 &
SDEVO_PID=$!
echo "   waiting up to ${INIT_WAIT}s for DEVO init"
for i in $(seq "$INIT_WAIT"); do
  grep -q "DEVO initialized" "$OUT_DIR/sdevo.log" && break
  kill -0 "$SDEVO_PID" 2>/dev/null || break
  sleep 1
done
grep -q "DEVO initialized" "$OUT_DIR/sdevo.log" || { echo "!! sdevo failed to init"; tail -30 "$OUT_DIR/sdevo.log"; exit 1; }

echo ">> [4/6] /sync global timer @ ${TIMER_HZ} Hz (wall; /use_sim_time now false)"
rostopic pub -s -r "$TIMER_HZ" /sync std_msgs/Time 'now' >"$OUT_DIR/timer.log" 2>&1 &

echo ">> [5/6] playing ${#BAGS[@]} bags @ ${PLAY_RATE}x with --clock"
rosbag play --clock -r "$PLAY_RATE" "${BAGS[@]}" >"$OUT_DIR/play.log" 2>&1
echo "   playback done; draining ${DRAIN_WAIT}s (upstream auto-saves 5 s after last voxel)"
sleep "$DRAIN_WAIT"

echo ">> [6/6] collecting trajectory"
if [ -s "$OUT_DIR/poses_tum_format.txt" ]; then
  cp -f "$OUT_DIR/poses_tum_format.txt" "$OUT_DIR/stamped_traj.tum"
  echo "   wrote stamped_traj.tum ($(grep -vc '^#' "$OUT_DIR/stamped_traj.tum") poses)"
else
  echo "   !! no poses_tum_format.txt produced"; tail -30 "$OUT_DIR/sdevo.log"
fi

kill "$SDEVO_PID" >/dev/null 2>&1
rosnode kill -a >/dev/null 2>&1; pkill -f rosmaster >/dev/null 2>&1
echo ">> done:"; ls -lh "$OUT_DIR"
exit 0
