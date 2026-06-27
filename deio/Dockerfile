# Faithful DEIO container — github.com/arclab-hku/DEIO (Guan et al., ICCV 2025).
# DEIO is a conda / PyTorch-2.3.1 / CUDA-11.8 project (DPVO + DEVO lineage) that also
# builds GTSAM with Python bindings. There is no upstream Dockerfile; this image follows
# environment.yml + the README build steps verbatim, pinning the upstream commit. No
# source edits. Running needs an NVIDIA GPU (build does not).
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      git wget ca-certificates build-essential cmake ninja-build \
      libboost-all-dev libtbb-dev libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

# --- Miniconda (provides the Python 3.10 the env pins) ---
ENV CONDA_DIR=/opt/conda PATH=/opt/conda/bin:$PATH
RUN wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/mc.sh \
 && bash /tmp/mc.sh -b -p $CONDA_DIR && rm /tmp/mc.sh && conda config --set always_yes true

# --- Upstream DEIO, pinned ---
ARG DEIO_COMMIT=47dcc275e9a0fd4fc00c130340e29452a9d510c5
RUN git clone https://github.com/arclab-hku/DEIO /opt/DEIO \
 && cd /opt/DEIO && git checkout $DEIO_COMMIT && git submodule update --init --recursive || true
WORKDIR /opt/DEIO

# --- Conda env (PyTorch 2.3.1 + cu118 + pytorch-scatter + evo + ...) ---
RUN conda env create -f environment.yml && conda clean -afy
SHELL ["conda", "run", "--no-capture-output", "-n", "DEIO", "/bin/bash", "-c"]

# --- DPVO/DEVO CUDA extensions (A5000 = sm_86) + numpy-quaternion ---
ENV TORCH_CUDA_ARCH_LIST="8.6"
RUN pip install --no-build-isolation . && pip install numpy-quaternion==2022.4.3

# --- GTSAM with Python bindings (README step) ---
RUN cd thirdparty/gtsam && mkdir -p build && cd build \
 && cmake .. -DGTSAM_BUILD_PYTHON=1 -DGTSAM_PYTHON_VERSION=3.10 \
      -DGTSAM_BUILD_TESTS=OFF -DGTSAM_BUILD_EXAMPLES_ALWAYS=OFF -DGTSAM_WITH_TBB=OFF \
 && make -j"$(nproc)" python-install

ENV PYTHONPATH=/opt/DEIO
# Default into the DEIO env for any `docker run`/`exec`.
RUN echo "source activate DEIO" >> /root/.bashrc
SHELL ["/bin/bash", "-c"]
CMD ["bash"]
