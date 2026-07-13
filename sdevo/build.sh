#!/usr/bin/env bash
# Build the SDEVO image ->  event-world/sdevo:latest
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cmd() { docker build -t event-world/sdevo:latest "$HERE"; }
if docker info >/dev/null 2>&1; then cmd; else sg docker -c "$(declare -f cmd); cmd"; fi
