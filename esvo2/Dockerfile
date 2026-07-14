# ESVO2 — direct stereo event VIO (Niu, Zhong, Lu, Shen, Gallego, Zhou; arXiv:2410.09374)
# Faithful container for github.com/NAIL-HNU/ESVO2 @ pinned commit. CPU-only (Ceres 1.14).
#
# Deps per upstream README/dependencies.yaml (ethz-asl shims + minkindr); only dvs_msgs is
# used from rpg_dvs_ros (drivers need libcaer, not used); minkindr_python is ignored so the
# catkin_boost_python_buildtool/numpy_eigen chain is not needed (esvo2_core uses only the
# C++ minkindr + minkindr_conversions). No algorithm/source edits.
FROM ros:noetic-perception

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential cmake \
    libceres-dev libyaml-cpp-dev libgflags-dev libgoogle-glog-dev libfmt-dev \
    ros-noetic-image-geometry ros-noetic-pcl-ros ros-noetic-tf-conversions \
    ros-noetic-dynamic-reconfigure ros-noetic-cv-bridge ros-noetic-image-transport \
    python3-catkin-tools python3-osrf-pycommon \
    autoconf automake libtool libeigen3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /catkin_ws/src
ARG ESVO2_COMMIT=9381fe9dda5f5dd528eb63a8af2e3a49a1db3a63
RUN git clone https://github.com/NAIL-HNU/ESVO2.git && \
    cd ESVO2 && git checkout ${ESVO2_COMMIT}

# dependency packages (upstream tracks 'master'; exact commits recorded at build time)
RUN git clone --depth 1 https://github.com/catkin/catkin_simple.git && \
    git clone --depth 1 https://github.com/uzh-rpg/rpg_dvs_ros.git && \
    git clone --depth 1 https://github.com/ethz-asl/gflags_catkin.git && \
    git clone --depth 1 https://github.com/ethz-asl/glog_catkin.git && \
    git clone --depth 1 https://github.com/ethz-asl/minkindr.git && \
    git clone --depth 1 https://github.com/ethz-asl/minkindr_ros.git && \
    git clone --depth 1 https://github.com/ethz-asl/eigen_catkin.git && \
    git clone --depth 1 https://github.com/ethz-asl/eigen_checks.git && \
    for d in catkin_simple rpg_dvs_ros gflags_catkin glog_catkin minkindr minkindr_ros eigen_catkin eigen_checks ESVO2; do \
      echo "$d $(git -C $d rev-parse HEAD)" >> /catkin_ws/PINNED_COMMITS.txt; done && \
    cat /catkin_ws/PINNED_COMMITS.txt
RUN cd rpg_dvs_ros && for d in */; do case "$d" in dvs_msgs/) ;; *) touch "$d/CATKIN_IGNORE";; esac; done && \
    cd ../minkindr && for d in */; do case "$d" in minkindr/) ;; *) touch "$d/CATKIN_IGNORE";; esac; done && \
    cd ../minkindr_ros && for d in */; do case "$d" in minkindr_conversions/) ;; *) touch "$d/CATKIN_IGNORE";; esac; done

# Upstream build fixes (build plumbing only, no algorithm code):
#  (a) events_repacking_tool calls add_message_files() before any catkin find_package
#      loads the genmsg macros -> "Unknown CMake command" in a clean workspace. esvo2_core
#      #includes its generated V_ba_bg.h, so the package must build.
#  (b) esvo2_core uses that header but does not declare the dependency -> build-order race.
RUN sed -i 's/^add_message_files(/find_package(catkin REQUIRED COMPONENTS message_generation std_msgs)\nadd_message_files(/' \
      ESVO2/events_repacking_tool/CMakeLists.txt && \
    echo 'cs_export()' >> ESVO2/events_repacking_tool/CMakeLists.txt && \
    sed -i 's|<depend>dvs_msgs</depend>|<depend>dvs_msgs</depend>\n  <depend>events_repacking_tool</depend>|' \
      ESVO2/esvo2_core/package.xml && \
    grep -n 'events_repacking_tool' ESVO2/esvo2_core/package.xml

RUN bash -c "source /opt/ros/noetic/setup.bash && cd /catkin_ws && \
    catkin init && catkin config --cmake-args -DCMAKE_BUILD_TYPE=Release && catkin build"

RUN echo "source /opt/ros/noetic/setup.bash && source /catkin_ws/devel/setup.bash" >> /root/.bashrc
WORKDIR /catkin_ws
ENTRYPOINT ["/bin/bash"]
