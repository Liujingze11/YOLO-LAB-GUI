#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
ISAT_RUNTIME_PYTHON="${ISAT_PYTHON:-$HOME/miniconda3/envs/isat_env/bin/python}"
if ! command -v "$ISAT_RUNTIME_PYTHON" >/dev/null 2>&1; then
  ISAT_RUNTIME_PYTHON=python3
fi
if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$ISAT_RUNTIME_PYTHON" --target "$PWD/.runtime/python" -r requirements-model-runtime.txt
else
  "$ISAT_RUNTIME_PYTHON" -m pip install --target "$PWD/.runtime/python" -r requirements-model-runtime.txt
fi
PYTHONPATH="$PWD/.runtime/python:$PWD${PYTHONPATH:+:$PYTHONPATH}" "$ISAT_RUNTIME_PYTHON" -c 'import PyQt5, matplotlib, ultralytics, requests; print("ISAT model development runtime is ready")'
