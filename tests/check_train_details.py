#!/usr/bin/env python3
"""One-off: step-3 ports must work.

Leg 1: dataset info hint reads data.yaml and shows nc + root.
Leg 2: _validate_config reports the four pre-train problems.
Leg 3: loss metrics render into the progress bar format.
Leg 4: resume training passes data/imgsz/batch/device to model.train.
Leg 5: logs tab auto-refreshes on show.
"""
import os
import sys
import tempfile
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


from main import MainWindow

win = MainWindow()
tt = win._train_tab

tmp = Path(tempfile.mkdtemp())

# ── Leg 1: dataset info hint ──
yaml_path = tmp / "data.yaml"
yaml_path.write_text("path: .\nnames:\n  0: cat\n  1: dog\n", encoding="utf-8")
tt.tr_data_yaml.setCurrentText(str(yaml_path))
tt._update_dataset_info()
text = tt.dataset_info.text()
expect("nc=2" in text and str(tmp.resolve()) in text,
       f"dataset hint shows nc and root (got {text!r})")

# ── Leg 2: pre-train validation ──
from core.config import TrainConfig

tt._model_file_ok = lambda p: False
bad = TrainConfig()
bad.data_yaml = ""
bad.model_file = "nope.pt"
bad.results_dir = ""
bad.experiment_name = "   "
errs = tt._validate_config(bad)
expect(len(errs) == 4, f"four problems reported (got {len(errs)}: {errs})")

tt._model_file_ok = lambda p: True
good = TrainConfig()
good.data_yaml = str(yaml_path)
good.model_file = "yolov8n-seg.pt"
good.results_dir = str(tmp)
good.experiment_name = "exp1"
expect(tt._validate_config(good) == [], "clean config reports no problems")

# ── Leg 3: progress bar metrics text ──
tt._on_train_metrics({"epoch": 3, "total_epochs": 10,
                      "box_loss": 1.5, "seg_loss": 0.25, "cls_loss": 0.125, "dfl_loss": 0.5})
fmt = tt.tr_progress.format()
expect("Epoch 3/10" in fmt and "box=1.500" in fmt and "seg=0.250" in fmt,
       f"progress format shows epoch and losses (got {fmt!r})")

# ── Leg 4: resume passes overrides ──
import gui.train_engine as te


class StubYOLO:
    last = None

    def __init__(self, weights):
        self.weights = weights
        StubYOLO.last = self

    def train(self, **kw):
        self.train_kw = kw


te.YOLO = StubYOLO
te.append_train_log = lambda *a, **k: None
te.log_validation_result = lambda *a, **k: None

cfg = TrainConfig()
cfg.data_yaml = str(yaml_path)
cfg.results_dir = str(tmp / "res")
cfg.experiment_name = "exp1"
cfg.imgsz = 512
cfg.batch = 8
cfg.device = "1"
te.execute_resume_training(cfg)
kw = getattr(StubYOLO.last, "train_kw", {})
expect(kw.get("resume") is True and kw.get("data") == str(yaml_path)
       and kw.get("imgsz") == 512 and kw.get("batch") == 8 and kw.get("device") == "1",
       f"resume train gets overrides (got {kw})")

# ── Leg 5: logs tab auto-refresh on show ──
from PySide6.QtGui import QShowEvent
from gui.tabs.logs_tab import LogsTab

logs = LogsTab(path_history={})
calls = []
logs._refresh_lv_csv_list = lambda: calls.append("csv")
logs._refresh_lv_exp_list = lambda: calls.append("exp")
logs.showEvent(QShowEvent())
expect(calls == ["csv", "exp"], f"showEvent refreshes both lists (got {calls})")

print("ALL PASS")
