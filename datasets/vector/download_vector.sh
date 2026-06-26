#!/usr/bin/env bash
# Download a VECtor sequence (https://star-datasets.github.io/vector/) in ROS-bag
# form, fetching only the streams ESVIO needs. Ground truth is fetched as TUM txt.
#
# Usage:
#   ./download_vector.sh <sequence> [stream ...]
#   ./download_vector.sh desk-normal
#   ./download_vector.sh corner-slow left_event right_event imu gt_txt   # ESIO (no images)
#
# Default streams: left_event right_event left_camera right_camera imu gt_txt
# Files are saved to  <repo>/data/vector/<sequence>/  (gitignored).
#
# Requires gdown. Set GDOWN=/path/to/gdown, or it looks in PATH and
# ~/.venvs/evtools/bin/gdown.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"

SEQ="${1:?usage: download_vector.sh <sequence> [streams...]}"; shift || true
STREAMS=("$@")
if [ "${#STREAMS[@]}" -eq 0 ]; then
  STREAMS=(left_event right_event imu gt_txt left_camera right_camera)
fi

OUT="$ROOT/data/vector/$SEQ"; mkdir -p "$OUT"
CACHE="$ROOT/data/vector/.vector_download.html"
PAGE_URL="https://star-datasets.github.io/vector/download/"

GDOWN="${GDOWN:-}"
if [ -z "$GDOWN" ]; then
  if   command -v gdown >/dev/null 2>&1;            then GDOWN="gdown"
  elif [ -x "$HOME/.venvs/evtools/bin/gdown" ];     then GDOWN="$HOME/.venvs/evtools/bin/gdown"
  else echo "ERROR: gdown not found. Try: python3 -m venv ~/.venvs/evtools && ~/.venvs/evtools/bin/pip install gdown" >&2; exit 1
  fi
fi

if [ ! -s "$CACHE" ]; then
  echo ">> fetching index $PAGE_URL"
  curl -sSL --max-time 60 "$PAGE_URL" -o "$CACHE"
fi

# Parse the per-sequence link block. Each small-scale row lists 15 Google-Drive
# links in a fixed order; we map them to stream names positionally.
map_json="$(python3 - "$CACHE" "$SEQ" <<'PY'
import sys,re,json
page=open(sys.argv[1]).read(); seq=sys.argv[2]
idx=-1
for m in re.finditer(re.escape(seq), page):
    if 'left event' in page[m.end():m.end()+200]:
        idx=m.start(); break
if idx<0:
    print('{}'); sys.exit(0)
region=page[idx:idx+6000]
links=re.findall(r'href="https://drive\.google\.com/file/d/([^/]+)/', region)
order=['left_event','left_event_hdf5','right_event','right_event_hdf5',
       'left_camera','left_camera_zip','right_camera','right_camera_zip',
       'depth','depth_zip','imu','imu_txt','gt','gt_txt','scene']
out={order[i]:links[i] for i in range(min(len(order),len(links)))}
print(json.dumps(out))
PY
)"
echo ">> parsed links: $map_json"
[ "$map_json" = "{}" ] && { echo "ERROR: sequence '$SEQ' not found on index page" >&2; exit 1; }

get_id(){ python3 -c "import json,sys;print(json.loads(sys.argv[1]).get(sys.argv[2],''))" "$map_json" "$1"; }
ext_for(){ case "$1" in gt_txt) echo txt;; *) echo bag;; esac; }

fail=0
for s in "${STREAMS[@]}"; do
  id="$(get_id "$s")"
  if [ -z "$id" ]; then echo "!! no link for stream '$s' in $SEQ" >&2; fail=1; continue; fi
  dest="$OUT/${SEQ}_${s}.$(ext_for "$s")"
  if [ -s "$dest" ]; then echo "== already have $(basename "$dest")"; continue; fi
  echo ">> $s  ($id)  -> $(basename "$dest")"
  if "$GDOWN" "https://drive.google.com/uc?id=$id" -O "$dest.part"; then
    mv "$dest.part" "$dest"
  else
    echo "!! download failed for $s ($id)" >&2; rm -f "$dest.part"; fail=1
  fi
done
echo ">> done -> $OUT"; ls -lh "$OUT" || true
exit $fail
