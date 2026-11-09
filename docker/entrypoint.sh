#!/bin/bash
set -euo pipefail
cd /app
exec python -m yolo_backprop.main "$@"
