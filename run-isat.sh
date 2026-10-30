#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
ISAT_RUNTIME_PYTHON="${ISAT_PYTHON:-}"
if [[ -z "$ISAT_RUNTIME_PYTHON" ]]; then
  if [[ -x "$HOME/miniconda3/envs/isat_env/bin/python" ]]; then
    ISAT_RUNTIME_PYTHON="$HOME/miniconda3/envs/isat_env/bin/python"
  else
    ISAT_RUNTIME_PYTHON=python3
  fi
fi
export PYTHONPATH="$PWD/.runtime/python:$PWD${PYTHONPATH:+:$PYTHONPATH}"
export QT_API=pyqt5
exec "$ISAT_RUNTIME_PYTHON" -m ISAT.main "$@"
