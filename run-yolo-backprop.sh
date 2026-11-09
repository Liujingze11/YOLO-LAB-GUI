#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
YOLO_RUNTIME_PYTHON="${YOLO_BACKPROP_PYTHON:-${ISAT_PYTHON:-}}"
if [[ -z "$YOLO_RUNTIME_PYTHON" ]]; then
  if [[ -x "$HOME/miniconda3/envs/isat_env/bin/python" ]]; then
    YOLO_RUNTIME_PYTHON="$HOME/miniconda3/envs/isat_env/bin/python"
  else
    YOLO_RUNTIME_PYTHON=python3
  fi
fi
export PYTHONPATH="$PWD/.runtime/python:$PWD${PYTHONPATH:+:$PYTHONPATH}"
export QT_API=pyqt5
exec "$YOLO_RUNTIME_PYTHON" -m yolo_backprop.main "$@"
