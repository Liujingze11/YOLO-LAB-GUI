#!/usr/bin/env python3
"""One-off regression check: GUI panel params must reach the engine config.

Simulates the GUI -> engine transport:
  GUI side:    full TrainConfig -> per-run YAML file
  engine side: defaults -> user config -> run config file -> explicit CLI args
"""
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from core.config import TrainConfig, load_effective_config, save_run_config


def expect(cond, msg):
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)
    print(f"ok: {msg}")


cfg = TrainConfig()
cfg.data_yaml = "/tmp/fake_data.yaml"
cfg.model_file = "yolov8n.pt"
cfg.results_dir = "/tmp/r"
cfg.log_dir = "/tmp/l"
cfg.epochs = 42
cfg.lr0 = 0.123
cfg.optimizer = "SGD"
cfg.mosaic = 0.7
cfg.dropout = 0.25
cfg.hsv_h = 0.001
cfg.weight_decay = 0.99
cfg.cos_lr = False

tmp = Path(tempfile.mkstemp(suffix=".yaml")[1])
save_run_config(cfg, tmp)

merged = load_effective_config(run_config_file=tmp)
expect(merged.lr0 == 0.123, f"lr0 crosses the boundary (got {merged.lr0})")
expect(merged.optimizer == "SGD", f"optimizer crosses (got {merged.optimizer})")
expect(merged.mosaic == 0.7, f"mosaic crosses (got {merged.mosaic})")
expect(merged.dropout == 0.25, f"dropout crosses (got {merged.dropout})")
expect(merged.hsv_h == 0.001, f"hsv_h crosses (got {merged.hsv_h})")
expect(merged.weight_decay == 0.99, f"weight_decay crosses (got {merged.weight_decay})")
expect(merged.cos_lr is False, f"cos_lr crosses (got {merged.cos_lr})")
expect(
    merged.epochs == 42 and merged.data_yaml == "/tmp/fake_data.yaml",
    "basic fields still cross",
)

over = load_effective_config(cli_args={"lr0": 0.9, "epochs": 5}, run_config_file=tmp)
expect(over.lr0 == 0.9 and over.epochs == 5, "explicit CLI args still win")
expect(over.optimizer == "SGD", "run file beats defaults/user config")

tmp.unlink()
print("ALL PASS")
