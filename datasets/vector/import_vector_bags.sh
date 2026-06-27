#!/usr/bin/env bash
# Import VECtor "<seq>.synced.<stream>.<ext>" rosbags from a local directory into
# data/vector/<seq>/ with this pipeline's naming. Default: move (instant on same FS).
#   import_vector_bags.sh <src_dir>            # move
#   import_vector_bags.sh <src_dir> --copy     # copy
#   import_vector_bags.sh <src_dir> --dry-run  # show planned moves only
# Skips duplicate "(1)" files, .hdf5, and gt.bag (we use gt.txt).
set -euo pipefail
SRC="${1:?usage: import_vector_bags.sh <src_dir> [--copy|--dry-run]}"
MODE="${2:-move}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; DATA="$ROOT/data/vector"
shopt -s nullglob
act(){ case "$MODE" in
  --dry-run) echo "  $(basename "$1")  ->  ${2#$DATA/}";;
  --copy)    cp -n "$1" "$2" && echo "  copied ${2#$DATA/}";;
  *)         mv -n "$1" "$2" && echo "  moved  ${2#$DATA/}";; esac; }
for f in "$SRC"/*.synced.*; do
  bn="$(basename "$f")"
  case "$bn" in *"(1)"*|*.hdf5|*.gt.bag) continue;; esac
  seqraw="${bn%%.synced.*}"; rest="${bn#*.synced.}"
  seq="$(echo "$seqraw" | sed 's/_/-/g; s/[0-9]*$//')"   # corner_slow1 -> corner-slow
  case "$rest" in
    left_event.bag)   d="${seq}_left_event.bag";;
    right_event.bag)  d="${seq}_right_event.bag";;
    left_camera.bag)  d="${seq}_left_camera.bag";;
    right_camera.bag) d="${seq}_right_camera.bag";;
    imu.bag)          d="${seq}_imu.bag";;
    gt.txt)           d="${seq}_gt_txt.txt";;
    *) continue;;
  esac
  mkdir -p "$DATA/$seq"; act "$f" "$DATA/$seq/$d"
done
