# Clean build of dpvo-clean (base DEVO). Upstream Dockerfile bugs fixed:
#  - opencv GUI libs (libxcb etc.) for the headless CUDA image
#  - torch PINNED to 2.6.0+cu124 (matches the cu12.4 base; the newest torch with a py3.12
#    torch-scatter wheel — unpinned >=2.7 pulled torch 2.12+cu130 which has no torch-scatter)
#  - COPY setup.py (so the 3 CUDA exts actually build) + non-editable install (they persist)
#  - TORCH_CUDA_ARCH_LIST=8.6 (A5000) since there's no GPU at build time
FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libxcb1 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*
RUN uv python install 3.12
RUN uv venv --seed --python=3.12 /venv
ENV TORCH_CUDA_ARCH_LIST="8.6"
RUN . /venv/bin/activate && uv pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
RUN . /venv/bin/activate && uv pip install torch-scatter -f "https://data.pyg.org/whl/torch-2.6.0+cu124.html"
COPY pyproject.toml setup.py /project/
COPY src /project/src
RUN . /venv/bin/activate && uv pip install /project
WORKDIR /project
ENTRYPOINT ["/usr/bin/sh", "-c", ". /venv/bin/activate && \"$@\"", "--"]
