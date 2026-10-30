"""
后台工作线程 —— 在子进程中运行训练/推理/工具脚本，实时读取输出。
"""
from __future__ import annotations

import os
import re
import subprocess
import signal
import threading
import time
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

ROOT = Path(__file__).resolve().parent.parent


class _BaseWorker(QThread):
    """子进程工作线程基类。"""

    log_line = pyqtSignal(str)
    finished_ok = pyqtSignal()
    failed = pyqtSignal(str)
    stopped = pyqtSignal()

    def __init__(self, cmd: list[str]):
        super().__init__()
        self._cmd = cmd
        self._process: subprocess.Popen | None = None
        self._aborted = False
        self._cancelled = threading.Event()

    def run(self) -> None:
        if self._cancelled.is_set():
            self.stopped.emit()
            return
        try:
            self._process = subprocess.Popen(
                self._cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8", errors="replace",
                start_new_session=(os.name != "nt"),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
                bufsize=1,
                cwd=str(ROOT),
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
        except Exception as e:
            self.failed.emit(f"启动进程失败: {e}")
            return

        monitor = threading.Thread(target=self._watch_cancellation, daemon=True)
        monitor.start()
        try:
            for line in self._process.stdout:
                stripped = line.rstrip("\n").rstrip("\r")
                if stripped:
                    self.log_line.emit(stripped)
                    self._on_line(stripped)
        except (IOError, OSError):
            pass

        self._process.wait()
        self._process.stdout.close()
        monitor.join()
        if self._aborted:
            self.stopped.emit()
        elif self._process.returncode == 0:
            self.finished_ok.emit()
        else:
            self.failed.emit(f"进程退出码: {self._process.returncode}")

    def _on_line(self, line: str) -> None:
        """子类可覆盖此方法来解析进度等。"""

    def _watch_cancellation(self):
        process = self._process
        while process.poll() is None:
            if self._cancelled.wait(.05):
                self._terminate_group(process)
                return
        self._terminate_group(process)

    @staticmethod
    def _terminate_group(process):
        def send(sig):
            try:
                if os.name == 'nt':
                    if sig == signal.SIGINT: process.send_signal(signal.CTRL_BREAK_EVENT)
                    elif sig == signal.SIGTERM: process.terminate()
                    else: subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else: os.killpg(process.pid, sig)
            except (ProcessLookupError, OSError): pass
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
            send(sig)
            try: process.wait(timeout=2)
            except subprocess.TimeoutExpired: continue
            # The process leader may exit before a descendant holding stdout.
            if os.name != 'nt': send(signal.SIGTERM); send(signal.SIGKILL)
            break

    def stop(self) -> None:
        self._aborted = True
        self._cancelled.set()


class TrainWorker(_BaseWorker):
    """在子进程中运行训练脚本，解析 epoch 进度。"""

    progress = pyqtSignal(int)
    metrics_update = pyqtSignal(dict)

    def __init__(self, cmd: list[str]):
        super().__init__(cmd)
        self._last_epoch: int | None = None

    def _on_line(self, line: str) -> None:
        self._parse_metrics_line(line)
        self._parse_val_line(line)
        m = re.search(r"\b(\d+)\s*/\s*(\d+)\b", line)
        if not m:
            return
        cur, total = int(m.group(1)), int(m.group(2))
        low = line.lower()
        if 1 <= cur <= total and total >= 10 and not any(
            kw in low
            for kw in (
                "transfer", "gflops", "summary", "param", "module",
                "cuda", "gradient", "amp", "fuse",
            )
        ):
            self.progress.emit(cur)

    def _parse_metrics_line(self, line: str) -> None:
        """Parse Ultralytics per-epoch metrics from stdout table rows.

        Example line:
             1/150       2.5G      1.234      1.567     0.891      1.012        12        640
        """
        import re as _re

        m = _re.match(
            r"^\s*(\d+)\s*/\s*(\d+)\s+"    # epoch/total
            r"[\d.]+[GM]?\s+"               # GPU_mem
            r"([\d.]+)\s+"                  # box_loss
            r"([\d.]+)\s+"                  # seg_loss
            r"([\d.]+)\s+"                  # cls_loss
            r"([\d.]+)\s+"                  # dfl_loss
            r"\d+\s+"                       # Instances
            r"\d+",                         # Size
            line,
        )
        if not m:
            return

        try:
            epoch = int(m.group(1))
            total = int(m.group(2))
            self._last_epoch = epoch
            metrics = {
                "epoch": epoch,
                "total_epochs": total,
                "box_loss": float(m.group(3)),
                "seg_loss": float(m.group(4)),
                "cls_loss": float(m.group(5)),
                "dfl_loss": float(m.group(6)),
            }
            self.metrics_update.emit(metrics)
        except (ValueError, IndexError):
            pass  # skip unparseable rows silently

    def _parse_val_line(self, line: str) -> None:
        """Parse the Ultralytics validation summary row and emit mAP metrics.

        Example (segmentation, 8 metrics; detection has 4):
                     all        123        456      0.654  ...   0.371      0.289
        The trailing metric pair is the task-primary mAP50 / mAP50-95
        (mask for segmentation, box for detection).
        """
        parts = line.split()
        if len(parts) < 5 or parts[0] != "all":
            return
        try:
            nums = [float(p) for p in parts[1:]]
        except ValueError:
            return
        if len(nums) < 6 or self._last_epoch is None:
            return
        self.metrics_update.emit({
            "epoch": self._last_epoch,
            "mAP50": nums[-2],
            "mAP50_95": nums[-1],
        })


class InferWorker(_BaseWorker):
    """在子进程中运行推理脚本，解析图片进度。"""

    progress = pyqtSignal(int, int)  # cur, total

    def _on_line(self, line: str) -> None:
        low = line.lower()
        if "image" not in low:
            return
        m = re.search(r"\b(\d+)\s*/\s*(\d+)\b", line)
        if not m:
            return
        cur, total = int(m.group(1)), int(m.group(2))
        if 1 <= cur <= total:
            self.progress.emit(cur, total)


class ToolWorker(_BaseWorker):
    """在子进程中运行数据集工具脚本，只输出日志。"""


class ExportWorker(_BaseWorker):
    """在子进程中运行模型导出脚本，仅输出日志。"""
