#!/usr/bin/env bash
# Build the ESVIO image, faithful to volkbay/ESVIO @ pinned commit.
#
# Usage:
#   ./build.sh                 # builds event-world/esvio:latest
#   IMAGE=foo/bar:tag ./build.sh
#
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${IMAGE:-event-world/esvio:latest}"

echo ">> Building ${IMAGE}"
echo ">> Context: ${HERE}"
docker build -t "${IMAGE}" "${HERE}"
echo ">> Done. Image: ${IMAGE}"
docker images "${IMAGE%:*}" --format '   {{.Repository}}:{{.Tag}}  {{.Size}}'
