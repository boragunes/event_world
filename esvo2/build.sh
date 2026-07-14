#!/usr/bin/env bash
# Build the ESVO2 image ->  event-world/esvo2:latest  (CPU-only)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! docker info >/dev/null 2>&1; then exec sg docker -c "docker build -t event-world/esvo2:latest '$HERE'"; fi
docker build -t event-world/esvo2:latest "$HERE"
