#!/usr/bin/env python3
"""End-to-end smoke: GUI transport -> engine -> ultralytics, verify params bite.

Builds a tiny synthetic detect dataset, fills a TrainConfig the way the GUI
panel does, ships it via the per-run YAML transport, runs gui/train_engine.py
exactly like train_tab._on_start_train, then checks the training's args.yaml.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

GUI_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GUI_REPO))

import numpy as np
from PIL import Image

sys.path.insert(0, str(GUI_REPO))
from core.config import TrainConfig, save_run_config

tmp = Path(tempfile.mkdtemp(prefix="yolo_e2e_"))

# ── tiny detect dataset: 6 imgs (4 train / 2 val), one box each ──
for split, n in (("train", 4), ("val", 2)):
    (tmp / "images" / split).mkdir(parents=True)
    (tmp / "labels" / split).mkdir(parents=True)
    for i in range(n):
        img = (np.random.rand(320, 320, 3) * 255).astype("uint8")
        img[100:180, 120:200] = [200, 40, 40]  # a visible rectangle
        Image.fromarray(img).save(tmp / "images" / split / f"{split}_{i}.jpg")
        (tmp / "labels" / split / f"{split}_{i}.txt").write_text("0 0.5 0.4375 0.25 0.25\n")

data_yaml = tmp / "data.yaml"
data_yaml.write_text(
    f"path: {tmp}\ntrain: images/train\nval: images/val\nnames:\n  0: block\n",
    encoding="utf-8",
)

# ── config exactly as the GUI panel builds it (1a transport) ──
cfg = TrainConfig()
cfg.data_yaml = str(data_yaml)
cfg.model_file = str(Path(__file__).resolve().parent.parent / "yolo26n.pt")
cfg.results_dir = str(tmp / "results")
cfg.log_dir = str(tmp / "logs")
cfg.epochs = 2
cfg.imgsz = 320
cfg.batch = 2
cfg.device = "cpu"
cfg.experiment_name = "smoke_lr0"
cfg.lr0 = 0.123
cfg.optimizer = "SGD"
cfg.mosaic = 0.7
cfg.translate = 0.222
cfg.use_augment = True

cfg_file = tmp / "run_cfg.yaml"
save_run_config(cfg, cfg_file)

# ── the exact command train_tab._on_start_train builds ──
cmd = [
    sys.executable, str(GUI_REPO / "gui" / "train_engine.py"),
    "--lang", "zh",
    "--no-interactive",
    "--config-file", str(cfg_file),
    "--mode", "1",
    "--data-yaml", cfg.data_yaml,
    "--model-file", cfg.model_file,
    "--results-dir", cfg.results_dir,
    "--log-dir", cfg.log_dir,
    "--epochs", str(cfg.epochs),
    "--imgsz", str(cfg.imgsz),
    "--batch", str(cfg.batch),
    "--device", cfg.device,
    "--name", cfg.experiment_name,
    "--use-augment",
]

print(f"running engine: epochs={cfg.epochs} imgsz={cfg.imgsz} ...", flush=True)
proc = subprocess.run(cmd, cwd=str(GUI_REPO), capture_output=True, text=True, timeout=600)
tail = "\n".join((proc.stdout or "").strip().splitlines()[-6:])
print(f"engine exit={proc.returncode}\n--- engine tail ---\n{tail}\n-------------------")
if proc.returncode != 0:
    print("FAIL: engine exited non-zero")
    sys.exit(1)

# ── verify the params actually reached ultralytics ──
import yaml as pyyaml

args_file = tmp / "results" / "smoke_lr0" / "args.yaml"
if not args_file.is_file():
    print(f"FAIL: {args_file} missing (training produced no args.yaml)")
    sys.exit(1)
args = pyyaml.safe_load(args_file.read_text(encoding="utf-8"))

checks = [
    ("lr0", 0.123),
    ("optimizer", "SGD"),
    ("mosaic", 0.7),
    ("translate", 0.222),
    ("epochs", 2),
    ("imgsz", 320),
    ("batch", 2),
]
failed = False
for key, want in checks:
    got = args.get(key)
    ok = (abs(got - want) < 1e-9) if isinstance(want, float) else got == want
    print(f"{'ok' if ok else 'FAIL'}: args.yaml {key} = {got!r} (want {want!r})")
    failed |= not ok

print("ALL PASS" if not failed else "SMOKE FAILED")
sys.exit(1 if failed else 0)
