#!/usr/bin/env python3
"""One-off: GPU components ported from YOLO-LAB must work in YOLO-LAB-GUI.

Leg 1: locale files contain all gpu.*/welcome.* keys (4 languages).
Leg 2: gui/gpu_manager helpers + check_gpu_capability branches.
Leg 3: gui/device pseudo-device entries.
Leg 4: welcome wizard first-run marker round trip + construction.
"""
import json
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


# ── Leg 1: locale keys (behavioral; no new-module imports here) ──
REQUIRED_KEYS = [
    "gpu.check_title", "gpu.checking", "gpu.dev_needs_cuda_torch", "gpu.device_cpu",
    "gpu.device_gpu_download", "gpu.download_done", "gpu.download_failed",
    "gpu.download_prompt", "gpu.download_title", "gpu.downloading",
    "gpu.install_failed", "gpu.install_manual", "gpu.install_success",
    "gpu.install_title", "gpu.no_amd", "gpu.no_nvidia", "gpu.restart_needed",
    "welcome.data_ready", "welcome.env_summary", "welcome.gpu_cpu",
    "welcome.gpu_need_cuda", "welcome.gpu_need_setup", "welcome.gpu_ready",
    "welcome.heading", "welcome.models", "welcome.start", "welcome.tip",
    "welcome.title",
]
for lang in ("zh", "en", "es", "fr"):
    data = json.loads((REPO / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_KEYS if k not in data]
    expect(not missing, f"{lang}.json has all {len(REQUIRED_KEYS)} gpu/welcome keys (missing: {missing})")

# ── Leg 2: gpu_manager ──
import gui.gpu_manager as gm

tmp = Path(tempfile.mkdtemp())
gm.get_user_data_dir = lambda: tmp  # isolate marker side effects

expect(str(gm.get_gpu_dir()).endswith("gpu"), "get_gpu_dir composes under user data dir")
expect(not gm.has_gpu_ready_marker(), "marker absent initially")
gm.get_gpu_ready_file().parent.mkdir(parents=True, exist_ok=True)
gm.get_gpu_ready_file().write_text("{}")
expect(gm.has_gpu_ready_marker(), "marker detected after creation")

# capability state machine (deterministic via monkeypatch)
gm.has_gpu_ready_marker = lambda: False  # isolate from the real marker just created
gm.is_cuda_available = lambda: False
gm._check_nvidia_driver = lambda: (True, "RTX 3090")
gm._check_amd_driver = lambda: False
gm.platform = type("P", (), {"system": staticmethod(lambda: "Linux")})
gm.is_frozen = lambda: False

cap = gm.check_gpu_capability()
expect(cap["status"] == "dev_needs_cuda_torch" and "RTX 3090" in cap["message"],
       f"dev mode without cuda torch -> dev_needs_cuda_torch (got {cap['status']})")

gm.is_frozen = lambda: True
cap = gm.check_gpu_capability()
expect(cap["status"] == "needs_download" and cap["download_size_gb"] == 2.5,
       f"frozen without cuda torch -> needs_download (got {cap['status']})")

gm.is_frozen = lambda: False
gm.has_gpu_ready_marker = lambda: True
cap = gm.check_gpu_capability()
expect(cap["status"] == "needs_restart", f"marker present -> needs_restart (got {cap['status']})")

gm.has_gpu_ready_marker = lambda: False
gm._check_nvidia_driver = lambda: (False, "")
gm._check_amd_driver = lambda: True
cap = gm.check_gpu_capability()
expect(cap["status"] == "has_amd", f"amd driver -> has_amd (got {cap['status']})")

gm._check_amd_driver = lambda: False
cap = gm.check_gpu_capability()
expect(cap["status"] == "no_nvidia", f"no driver -> no_nvidia (got {cap['status']})")

gm._check_nvidia_driver = lambda: (True, "RTX 3090")
gm.is_cuda_available = lambda: True
import types
_real_torch = sys.modules.get("torch")
sys.modules["torch"] = types.SimpleNamespace(
    cuda=types.SimpleNamespace(is_available=lambda: True, device_count=lambda: 1,
                               get_device_name=lambda i: "RTX 3090"))
try:
    cap = gm.check_gpu_capability()
finally:
    if _real_torch is not None:
        sys.modules["torch"] = _real_torch
    else:
        del sys.modules["torch"]
expect(cap["status"] == "cuda_ready" and cap["gpu_name"] == "RTX 3090",
       f"cuda torch ready -> cuda_ready (got {cap['status']}, name={cap['gpu_name']})")

# ── Leg 3: device pseudo entries ──
import gui.device as gd

gd.is_cuda_available = lambda: False
gd.has_gpu_ready_marker = lambda: False
gd.platform = type("P", (), {"system": staticmethod(lambda: "Linux")})
devs = gd.get_available_devices()
expect(("gpu", "GPU (点击检测)") in devs, f"pseudo GPU entry when nothing ready (got {devs})")

gd.has_gpu_ready_marker = lambda: True
devs = gd.get_available_devices()
expect(any(d[0] == "gpu" and "重启" in d[1] for d in devs),
       f"restart hint after bundle marker (got {devs})")

expect(gd.get_default_device() in ("cpu", "0", "mps"), "default device sane")

# ── Leg 4: welcome wizard ──
import gui.welcome_wizard as ww

ww._WELCOME_MARKER = tmp / ".welcome_shown"
expect(ww.is_first_run(), "first run detected")
ww.mark_welcome_done()
expect(not ww.is_first_run(), "marker suppresses wizard")

import gui.gpu_manager as gm2
gm2.check_gpu_capability = lambda: {
    "status": "cuda_ready", "gpu_name": "RTX 3090", "download_size_gb": None, "message": ""}
wiz = ww.WelcomeWizard()
expect(wiz.windowTitle() != "", "wizard constructs headless")
wiz.close()

print("ALL PASS")
