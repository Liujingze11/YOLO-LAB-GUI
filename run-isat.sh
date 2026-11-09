#!/usr/bin/env bash
# Compatibility entry for existing desktop shortcuts and local launch commands.
set -euo pipefail
exec "$(dirname -- "${BASH_SOURCE[0]}")/run-yolo-backprop.sh" "$@"
