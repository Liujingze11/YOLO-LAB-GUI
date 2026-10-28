#!/usr/bin/env python3
"""One-off: settings tab's two dead spots must become real.

Leg 1: reset_splitter_requested actually resets TrainTab splitter sizes (via MainWindow wiring).
Leg 2: _save_defaults persists to a settings file and values restore on rebuild.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from PySide6.QtWidgets import QApplication, QMessageBox

app = QApplication.instance() or QApplication([])

# The save dialog must not block headless runs.
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)


def expect(cond, msg):
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)
    print(f"ok: {msg}")


# Qt clamps hidden-splitter sizes to widget minimums, so exact default pixel
# ratios are unachievable; the real contract is: emitting the signal has the
# same effect as setSizes(defaults), and does so deterministically.

MAIN_DEFAULTS = [200, 180, 170, 130, 220]
CHART_DEFAULTS = [400, 360]

# ── Leg 1: splitter reset wiring (behavioral) ──
from main import MainWindow

win = MainWindow()
win._train_tab._splitter.setSizes([10, 10, 10, 10, 100])
win._train_tab._chart_splitter.setSizes([50, 500])
win._settings_tab.reset_splitter_requested.emit()
got_main = win._train_tab._splitter.sizes()
got_chart = win._train_tab._chart_splitter.sizes()

# reference: the effect of setSizes(defaults) in this exact state
win._train_tab._splitter.setSizes(MAIN_DEFAULTS)
win._train_tab._chart_splitter.setSizes(CHART_DEFAULTS)
expect(got_main == win._train_tab._splitter.sizes(),
       f"emit == setSizes(defaults) for main splitter (got {got_main})")
expect(got_chart == win._train_tab._chart_splitter.sizes(),
       f"emit == setSizes(defaults) for chart splitter (got {got_chart})")

# deterministic: a different distorted state resets to the same result
win._train_tab._splitter.setSizes([700, 200, 200, 150, 300])
win._settings_tab.reset_splitter_requested.emit()
expect(win._train_tab._splitter.sizes() == got_main,
       "reset is deterministic across distorted states")

# ── Leg 2: defaults persistence round-trip ──
import core.config as cc
from gui.tabs.settings_tab import SettingsTab
from gui.widgets import path_combo_get

cc._SETTINGS_PATH = Path(tempfile.mkdtemp()) / "settings.yaml"  # isolate from real user file

st = SettingsTab()
st.default_dataset.setCurrentText("/tmp/my_dataset")
st.default_model_dir.setCurrentText("/tmp/my_models")
st._save_defaults()

data = cc.load_user_settings()
expect(data.get("default_dataset_dir") == "/tmp/my_dataset",
       f"dataset dir persisted (got {data.get('default_dataset_dir')})")
expect(data.get("default_model_dir") == "/tmp/my_models",
       f"model dir persisted (got {data.get('default_model_dir')})")

st2 = SettingsTab()
expect(path_combo_get(st2.default_dataset) == "/tmp/my_dataset",
       f"dataset dir restored on rebuild (got {path_combo_get(st2.default_dataset)})")
expect(path_combo_get(st2.default_model_dir) == "/tmp/my_models",
       f"model dir restored on rebuild (got {path_combo_get(st2.default_model_dir)})")

print("ALL PASS")
