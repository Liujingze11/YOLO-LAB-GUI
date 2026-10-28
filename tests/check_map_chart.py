#!/usr/bin/env python3
"""One-off: mAP subplot must get a data source.

Leg 1: TrainWorker parses the Ultralytics validation summary row and emits mAP.
Leg 2: train_tab forwards mAP values into the training chart.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])


def expect(cond, msg):
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)
    print(f"ok: {msg}")


# ── Leg 1: parser emits mAP from val summary rows ──
from gui.workers import TrainWorker

w = TrainWorker(cmd=["echo"])
captured = []
w.metrics_update.connect(captured.append)

# val row before any training row: no epoch context, must be ignored
w._on_line("                 all        123        456      0.654      0.512      0.523      0.371      0.612      0.445      0.371      0.289")
expect(not any("mAP50" in m for m in captured),
       "val row before any epoch is ignored")

# seg training row (4 losses) — must still parse as before
w._on_line("     1/150       2.5G      1.234      1.567      0.891      1.012        12        640")
loss = next((m for m in captured if "box_loss" in m), None)
expect(loss is not None and loss["box_loss"] == 1.234 and loss["seg_loss"] == 1.567,
       f"loss row still parses (got {loss})")

# seg val summary row: 8 metrics, trailing pair = mask mAP50 / mAP50-95
w._on_line("                 all        123        456      0.654      0.512      0.523      0.371      0.612      0.445      0.371      0.289")
m = next((m for m in captured if "mAP50" in m), None)
expect(m is not None, "seg val summary row emits mAP")
expect(m.get("epoch") == 1 and abs(m.get("mAP50", -1) - 0.371) < 1e-9
       and abs(m.get("mAP50_95", -1) - 0.289) < 1e-9,
       f"seg mAP values and epoch correct (got {m})")

# detect-style val row: 4 metrics, trailing pair = box mAP
w._on_line("     2/150       2.5G      1.111      1.222      0.777      0.888        12        640")
w._on_line("                 all         50         88      0.91      0.83      0.87      0.72")
m2 = [m for m in captured if "mAP50" in m][-1]
expect(m2.get("epoch") == 2 and abs(m2.get("mAP50", -1) - 0.87) < 1e-9
       and abs(m2.get("mAP50_95", -1) - 0.72) < 1e-9,
       f"detect mAP values and epoch correct (got {m2})")

# per-class rows must not emit
n_before = len([m for m in captured if "mAP50" in m])
w._on_line("       person        10        22       0.5       0.4      0.45       0.3")
expect(len([m for m in captured if "mAP50" in m]) == n_before,
       "per-class rows are ignored")

# ── Leg 2: train_tab forwards mAP into the chart ──
from main import MainWindow

win = MainWindow()
win._train_tab._on_train_metrics({"epoch": 5, "mAP50": 0.55, "mAP50_95": 0.42})
chart = win._train_tab._train_chart
expect(any(abs(y - 0.55) < 1e-9 for _, y in chart._data["mAP50"]),
       f"mAP50 forwarded to chart (got {list(chart._data['mAP50'])})")
expect(any(abs(y - 0.42) < 1e-9 for _, y in chart._data["mAP50-95"]),
       f"mAP50-95 forwarded to chart (got {list(chart._data['mAP50-95'])})")

print("ALL PASS")
