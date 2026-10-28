"""Regression suites — run each check script as an isolated subprocess.

Each check_*.py is a self-contained offscreen-Qt verification script
(red-green-neutered during development).  They run as subprocesses so
their module-level monkeypatches cannot leak between suites.

Run all:  python -m pytest tests/ -q
"""
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent

SCRIPTS = [
    "check_param_flow.py",
    "check_settings_tab.py",
    "check_map_chart.py",
    "check_gpu_components.py",
    "check_gpu_flow.py",
    "check_wizard_wiring.py",
    "check_train_details.py",
]


@pytest.mark.parametrize("script", SCRIPTS)
def test_regression(script):
    proc = subprocess.run(
        [sys.executable, str(HERE / script)],
        capture_output=True, text=True, timeout=300,
    )
    assert proc.returncode == 0, (
        f"{script} FAILED\n--- stdout ---\n{proc.stdout}\n--- stderr tail ---\n{proc.stderr[-2000:]}"
    )
