# SDEVO (Stereo-DEVO) — Zhong, Niu, Zhou, RAL 2025 (arXiv:2509.08235)
# Faithful container for github.com/NAIL-HNU/SDEVO @ pinned commit.
#
# The system is hybrid: a C++ ROS Noetic node (image_representation, builds L/R event
# voxels online from a rosbag) + a Python ROS node (sdevo.py, the stereo DEVO fork).
# Upstream env: Ubuntu 20.04 + ROS Noetic + CUDA 11.x + conda py3.10 (torch 1.12.0+cu113).
#
# Documented deviations (no upstream code is modified):
#  1. THE CORE devo/devo.py SHIPS WITHOUT SOURCE. The upstream git tree contains only two
#     build artifacts of it: the egg in dist/ (py source, 15:32) and a cp310 bytecode in
#     devo/__pycache__/ (15:53, NEWER). They differ materially: the egg's update_depth()
#     is broken (NameError: min_depth undefined -> the egg cannot run at all) and its
#     block_matching() differs from the bytecode. We therefore run the authors' NEWEST
#     released artifact exactly: the .pyc, installed as a sourceless module
#     (devo/devo.pyc). No reconstruction, no patching.
#  2. python3.10 venv (matches upstream's conda python + env pins: torch 1.12.0+cu113,
#     torchvision 0.13.0, torch-scatter 2.1.0, numpy 1.26.4, scipy 1.15.3, ...). Because
#     sdevo.py imports ROS tf/tf2_ros whose stock Noetic binding (tf2_py) is cp38-only,
#     we additionally compile ros/geometry+geometry2 against python3.10 in an overlay
#     workspace (/tf_ws). (Upstream's own conda-py3.10 setup has the same incompatibility,
#     unaddressed in their README.)
#  3. Deterministic headless start order (see launch/voxel_vector_nodes.launch).
FROM nvidia/cuda:11.3.1-cudnn8-devel-ubuntu20.04

ENV DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC
# old CUDA images ship rotated NVIDIA apt keys; the toolkit is already in the image
RUN rm -f /etc/apt/sources.list.d/cuda.list /etc/apt/sources.list.d/nvidia-ml.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg2 lsb-release ca-certificates git build-essential cmake unzip \
    software-properties-common \
    python3-venv python3-dev python3-pip python3-numpy \
    libboost-python-dev libeigen3-dev libopencv-dev libyaml-cpp-dev \
    autoconf automake libtool \
    && rm -rf /var/lib/apt/lists/*

# conda python 3.10 (upstream's interpreter + tooling; required to execute the released
# cp310 bytecode; deadsnakes no longer serves focal)
RUN curl -L https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -o /tmp/mf.sh && \
    bash /tmp/mf.sh -b -p /opt/conda && rm /tmp/mf.sh && \
    /opt/conda/bin/conda create -y -n sdevo python=3.10 && /opt/conda/bin/conda clean -afy
ENV VPY=/opt/conda/envs/sdevo

# ROS Noetic (ros-base + the packages image_representation/sdevo.py need)
RUN curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
      -o /usr/share/keyrings/ros-archive-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros/ubuntu focal main" \
      > /etc/apt/sources.list.d/ros1.list && \
    apt-get update && apt-get install -y --no-install-recommends \
      ros-noetic-ros-base ros-noetic-cv-bridge ros-noetic-image-transport \
      ros-noetic-tf ros-noetic-tf2-ros ros-noetic-tf2-geometry-msgs ros-noetic-angles \
      python3-catkin-tools python3-osrf-pycommon \
    && rm -rf /var/lib/apt/lists/*

# ---------------- catkin workspace (system py3.8 toolchain) ----------------
WORKDIR /catkin_ws/src
ARG SDEVO_COMMIT=2b8a556c60d0f7b14a6f46e38d880b4642013891
RUN git clone https://github.com/NAIL-HNU/SDEVO.git && \
    cd SDEVO && git checkout ${SDEVO_COMMIT}

# deps per SDEVO/dependencies.yaml (upstream tracks 'master' for all; we record the
# exact commits used into /catkin_ws/PINNED_COMMITS.txt at build time)
RUN git clone --depth 1 https://github.com/catkin/catkin_simple.git && \
    git clone --depth 1 https://github.com/uzh-rpg/rpg_dvs_ros.git && \
    git clone --depth 1 https://github.com/ethz-asl/gflags_catkin.git && \
    git clone --depth 1 https://github.com/ethz-asl/glog_catkin.git && \
    git clone --depth 1 https://github.com/ethz-asl/eigen_catkin.git && \
    git clone --depth 1 https://github.com/ethz-asl/eigen_checks.git && \
    for d in catkin_simple rpg_dvs_ros gflags_catkin glog_catkin eigen_catkin eigen_checks SDEVO; do \
      echo "$d $(git -C $d rev-parse HEAD)" >> /catkin_ws/PINNED_COMMITS.txt; done && \
    cat /catkin_ws/PINNED_COMMITS.txt
# only dvs_msgs is needed from rpg_dvs_ros (the drivers need libcaer; not used here)
RUN cd rpg_dvs_ros && for d in */; do case "$d" in dvs_msgs/) ;; *) touch "$d/CATKIN_IGNORE";; esac; done

# deviation #1: install the authors' released bytecode as a sourceless module
RUN cd SDEVO/DEVO/devo && cp __pycache__/devo.cpython-310.pyc devo.pyc && \
    ls -la devo.pyc && [ ! -f devo.py ] && echo "sourceless devo.pyc in place"

# catkin build (isolated) -- the ethz-asl shim packages (gflags/glog_catkin) build their
# libraries as external projects, so dependents must configure only after they are BUILT;
# catkin_make's single configure pass cannot do that.
RUN bash -c "source /opt/ros/noetic/setup.bash && cd /catkin_ws && \
    catkin init && catkin config --cmake-args -DCMAKE_BUILD_TYPE=Release && catkin build"

# ---------------- python3.10 venv (deviation #2: upstream env pins) ----------------
RUN $VPY/bin/pip install -U pip wheel setuptools
RUN $VPY/bin/pip install \
      torch==1.12.0+cu113 torchvision==0.13.0+cu113 \
      --extra-index-url https://download.pytorch.org/whl/cu113
RUN $VPY/bin/pip install torch-scatter==2.1.0 \
      -f https://data.pyg.org/whl/torch-1.12.0+cu113.html
RUN $VPY/bin/pip install \
      numpy==1.26.4 opencv-python==4.6.0.66 scipy==1.15.3 evo==1.18.1 \
      h5py==3.10.0 hdf5plugin==4.4.0 yacs==0.1.8 pyyaml==6.0 tqdm==4.64.0 \
      pandas==1.4.3 matplotlib==3.5.1 plyfile tabulate && \
    $VPY/bin/pip install rospkg catkin_pkg netifaces defusedxml empy==3.3.4

# build the CUDA extensions (cuda_corr, cuda_ba, lietorch_backends) in-tree (editable):
# sdevo.py prepends the repo dir to sys.path, so everything resolves from the tree
ENV TORCH_CUDA_ARCH_LIST="8.6"
# torch 1.12's cpp_extension imports pkg_resources.packaging (removed in setuptools>=70)
RUN $VPY/bin/pip install "setuptools==69.5.1"
RUN cd /catkin_ws/src/SDEVO/DEVO && $VPY/bin/pip install --no-deps --no-build-isolation -e .

# ---------------- tf2 python bindings for py3.10 (overlay ws) ----------------
RUN mkdir -p /tf_ws/src && cd /tf_ws/src && \
    git clone --depth 1 -b noetic-devel https://github.com/ros/geometry.git && \
    git clone --depth 1 -b noetic-devel https://github.com/ros/geometry2.git && \
    echo "geometry $(git -C geometry rev-parse HEAD)" >> /catkin_ws/PINNED_COMMITS.txt && \
    echo "geometry2 $(git -C geometry2 rev-parse HEAD)" >> /catkin_ws/PINNED_COMMITS.txt && \
    cd geometry  && for d in */; do case "$d" in tf/) ;; *) touch "$d/CATKIN_IGNORE";; esac; done && \
    cd ../geometry2 && for d in */; do case "$d" in tf2/|tf2_py/|tf2_ros/|tf2_msgs/) ;; *) touch "$d/CATKIN_IGNORE";; esac; done
RUN bash -c "source /opt/ros/noetic/setup.bash && source /catkin_ws/devel/setup.bash && cd /tf_ws && \
    catkin init && catkin config --cmake-args -DCMAKE_BUILD_TYPE=Release \
      -DPYTHON_EXECUTABLE=$VPY/bin/python && catkin build && \
    $VPY/bin/python -c 'import sys; sys.path.insert(0,\"/tf_ws/devel/lib/python3/dist-packages\"); import tf2_py; print(\"tf2_py cp310 OK\")'"

# venv python first so `#!/usr/bin/env python3` (sdevo.py) gets torch
ENV PATH="/opt/conda/envs/sdevo/bin:${PATH}"
RUN echo "source /opt/ros/noetic/setup.bash && source /catkin_ws/devel/setup.bash && source /tf_ws/devel/setup.bash" >> /root/.bashrc
WORKDIR /catkin_ws
ENTRYPOINT ["/bin/bash"]
