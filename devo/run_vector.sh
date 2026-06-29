#!/usr/bin/env bash
# Run base DEVO on VECtor (Sim3, vision-only). Needs data/deio_vector/<scene>/ prepared
# (EventSlicer hdf5 + rectify_map_left.h5 + calib_undist_evs_left.txt + tss_imgs_us_left.txt
#  + poses_evs_left.txt). Usage: run_vector.sh [scene1 scene2 ...]
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
SCENES="${*:-corner_slow1 desk_normal1 sofa_fast1 mountain_fast1}"
mkdir -p "$HERE/data/devo_out"
docker run --rm --gpus all \
  -v "$HERE/devo:/project" \
  -v "$HERE/data/deio_vector:/data:ro" \
  -v "$HERE/data/devo_out:/out" \
  event-world/devo python /project/eval/evaluate_vector_ev.py --scenes $SCENES --outdir /out
