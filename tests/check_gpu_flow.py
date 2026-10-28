#!/usr/bin/env python3
"""One-off: the GPU setup flow must be wired into YOLO-LAB-GUI's train tab.

Leg 1: DownloadDialog.set_status_text exists and truncates.
Leg 2: device combo gets the pseudo GPU entry via gui.device.
Leg 3: picking pseudo GPU with no driver shows info and resets combo.
Leg 4: dev_needs_cuda_torch starts GpuInstallWorker with a status dialog.
Leg 5: needs_download starts GpuDownloadWorker with the release URL.
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


class StubSignal:
    def connect(self, fn):
        self.fn = fn


class MsgStub:
    calls = []
    Yes, No = 1, 2

    @staticmethod
    def question(parent, title, text, *a):
        MsgStub.calls.append("question")
        return MsgStub.Yes

    @staticmethod
    def information(parent, title, text, *a):
        MsgStub.calls.append("info")

    @staticmethod
    def critical(parent, title, text, *a):
        MsgStub.calls.append("crit")


# ── Leg 1: set_status_text ──
from gui.model_selector import DownloadDialog

dlg = DownloadDialog("test.bin")
dlg.set_status_text("x" * 250)
expect(dlg._status.text() == "x" * 100,
       f"set_status_text truncates to 100 chars (got {len(dlg._status.text())})")
dlg.close()

# ── set up train tab ──
from main import MainWindow
import gui.tabs.train_tab as ttm

win = MainWindow()
tt = win._train_tab

ttm.get_available_devices = lambda: [("cpu", "CPU"), ("gpu", "GPU (点击检测)")]
ttm.get_default_device = lambda: "cpu"
tt._refresh_devices()
expect(tt.tr_device.findData("gpu") >= 0, "pseudo GPU appears in device combo")

ttm.QMessageBox = MsgStub
import gui.gpu_manager as gm

gpu_idx = tt.tr_device.findData("gpu")

# ── Leg 3: no driver -> info + reset ──
MsgStub.calls.clear()
gm.check_gpu_capability = lambda: {
    "status": "no_nvidia", "gpu_name": None, "download_size_gb": None, "message": "no gpu"}
tt._on_device_selected(gpu_idx)
expect("info" in MsgStub.calls, f"info dialog on no_nvidia (got {MsgStub.calls})")
expect(tt.tr_device.currentIndex() == 0, "combo reset to CPU after no_nvidia")

# ── Leg 4: dev_needs_cuda_torch -> install worker ──
class InstallStub:
    started = 0

    def __init__(self):
        InstallStub.started += 1
        self.log_line = StubSignal()
        self.finished = StubSignal()

    def start(self):
        pass


gm.GpuInstallWorker = InstallStub
gm.check_gpu_capability = lambda: {
    "status": "dev_needs_cuda_torch", "gpu_name": "RTX 3090", "download_size_gb": None,
    "message": "need cuda torch"}
InstallStub.started = 0
tt._on_device_selected(gpu_idx)
expect(InstallStub.started == 1, f"install worker started (got {InstallStub.started})")
expect(tt._gpu_install_dialog is not None, "install dialog created")

# ── Leg 5: needs_download -> download worker with release URL ──
class DownloadStub:
    started = 0

    def __init__(self, url, dest):
        DownloadStub.started += 1
        self.url = url
        self.progress = StubSignal()
        self.finished = StubSignal()
        self.error_msg = StubSignal()

    def start(self):
        pass


gm.GpuDownloadWorker = DownloadStub
gm.check_gpu_capability = lambda: {
    "status": "needs_download", "gpu_name": "RTX 3090", "download_size_gb": 2.5,
    "message": "need bundle"}
DownloadStub.started = 0
tt._on_device_selected(gpu_idx)
expect(DownloadStub.started == 1, f"download worker started (got {DownloadStub.started})")
expect(tt._gpu_worker.url.endswith("gpu_bundle.zip"),
       f"download worker uses gpu_bundle release URL (got {tt._gpu_worker.url})")

print("ALL PASS")
