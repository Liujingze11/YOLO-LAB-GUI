#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
YOLO_RUNTIME_PYTHON="${YOLO_BACKPROP_PYTHON:-${ISAT_PYTHON:-$HOME/miniconda3/envs/isat_env/bin/python}}"
if ! command -v "$YOLO_RUNTIME_PYTHON" >/dev/null 2>&1; then
  YOLO_RUNTIME_PYTHON=python3
fi
if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$YOLO_RUNTIME_PYTHON" --target "$PWD/.runtime/python" -r requirements-model-runtime.txt
else
  "$YOLO_RUNTIME_PYTHON" -m pip install --target "$PWD/.runtime/python" -r requirements-model-runtime.txt
fi
PYTHONPATH="$PWD/.runtime/python:$PWD${PYTHONPATH:+:$PYTHONPATH}" "$YOLO_RUNTIME_PYTHON" -c 'import PyQt5, matplotlib, ultralytics, requests; print("YOLO-BACKPROP model development runtime is ready")'
