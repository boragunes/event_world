#!/bin/bash
# In-container orchestration for one ESVO2 run on VECtor (headless).
# Mirrors the upstream README recipe (roslaunch system_vector.launch + rosbag play --clock),
# with the GUI nodes removed and the trajectory written to /out. Belt-and-braces we also
# rosbag-record the tracking pose topic.
#
# Env: OUT_DIR, PLAY_RATE (default 1.0 = upstream real-time recipe), INIT_WAIT, DRAIN_WAIT.
# Positional args: bag files to play (container paths). VECtor's IMU topic /imu/data is
# remapped to the launch's expected /davis/left/imu at playback.
set -o pipefail
source /opt/ros/noetic/setup.bash
source /catkin_ws/devel/setup.bash
export ROS_MASTER_URI=http://localhost:11311 ROS_HOSTNAME=localhost

: "${OUT_DIR:?}"
PLAY_RATE="${PLAY_RATE:-1.0}"; INIT_WAIT="${INIT_WAIT:-10}"; DRAIN_WAIT="${DRAIN_WAIT:-8}"
BAGS=("$@")
mkdir -p "$OUT_DIR"

echo ">> [1/5] roscore"
roscore >"$OUT_DIR/roscore.log" 2>&1 &
until rostopic list >/dev/null 2>&1; do sleep 0.3; done

echo ">> [2/5] roslaunch system_vector_headless (image_representation L/R + mapping + tracking)"
roslaunch --wait /work/system_vector_headless.launch >"$OUT_DIR/esvo2_nodes.log" 2>&1 &
LAUNCH_PID=$!
sleep "$INIT_WAIT"

echo ">> [3/5] recording /esvo2_tracking/pose_pub"
rosbag record -O "$OUT_DIR/pose.bag" /esvo2_tracking/pose_pub __name:=poserec >"$OUT_DIR/record.log" 2>&1 &
sleep 2

echo ">> [4/5] playing ${#BAGS[@]} bags @ ${PLAY_RATE}x (--clock, /imu/data -> /davis/left/imu)"
rosbag play --clock -r "$PLAY_RATE" "${BAGS[@]}" /imu/data:=/davis/left/imu >"$OUT_DIR/play.log" 2>&1
echo "   playback done; draining ${DRAIN_WAIT}s"; sleep "$DRAIN_WAIT"

rosnode kill /poserec >/dev/null 2>&1 || true
sleep 1
echo ">> [5/5] clean shutdown (SIGINT roslaunch -> tracking node saves trajectory on destruction)"
kill -INT "$LAUNCH_PID" >/dev/null 2>&1; sleep 6

echo ">> outputs in $OUT_DIR:"
ls -lh "$OUT_DIR" || true
rosnode kill -a >/dev/null 2>&1; pkill -f rosmaster >/dev/null 2>&1
exit 0
