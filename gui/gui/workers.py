"""
后台工作线程 —— 在子进程中运行训练/推理脚本，实时读取输出。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal

ROOT = Path(__file__).resolve().parent.parent


class TrainWorker(QThread):
    """在子进程中运行 train_segment.py，解析 epoch 进度。"""

    log_line = Signal(str)
    progress = Signal(int)
    failed = Signal(str)
    finished_ok = Signal()
    stopped = Signal()

    def __init__(self, cmd: list[str]):
        super().__init__()
        self._cmd = cmd
        self._process: subprocess.Popen | None = None
        self._aborted = False

    def run(self) -> None:
        self._process = subprocess.Popen(
            self._cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(ROOT),
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        try:
            for line in self._process.stdout:
                stripped = line.rstrip("\n").rstrip("\r")
                if stripped:
                    self.log_line.emit(stripped)
                    self._maybe_emit_progress(stripped)
        except (IOError, OSError):
            pass
        self._process.wait()
        if self._aborted:
            self.stopped.emit()
        elif self._process.returncode == 0:
            self.finished_ok.emit()
        else:
            self.failed.emit(f"进程退出码: {self._process.returncode}")

    def _maybe_emit_progress(self, line: str) -> None:
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

    def stop(self) -> None:
        self._aborted = True
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()


class InferWorker(QThread):
    """在子进程中运行 predict_test.py，实时输出日志和图片进度。"""

    log_line = Signal(str)
    progress = Signal(int, int)  # cur, total
    failed = Signal(str)
    finished_ok = Signal()
    stopped = Signal()

    def __init__(self, cmd: list[str]):
        super().__init__()
        self._cmd = cmd
        self._process: subprocess.Popen | None = None
        self._aborted = False

    def run(self) -> None:
        self._process = subprocess.Popen(
            self._cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(ROOT),
        )
        try:
            for line in self._process.stdout:
                stripped = line.rstrip("\n").rstrip("\r")
                if stripped:
                    self.log_line.emit(stripped)
                    self._maybe_emit_progress(stripped)
        except (IOError, OSError):
            pass
        self._process.wait()
        if self._aborted:
            self.stopped.emit()
        elif self._process.returncode == 0:
            self.finished_ok.emit()
        else:
            self.failed.emit(f"进程退出码: {self._process.returncode}")

    def _maybe_emit_progress(self, line: str) -> None:
        """从 YOLO predict 输出中解析图片进度，如 'image 3/100 ...'。"""
        low = line.lower()
        if "image" not in low:
            return
        m = re.search(r"\b(\d+)\s*/\s*(\d+)\b", line)
        if not m:
            return
        cur, total = int(m.group(1)), int(m.group(2))
        if 1 <= cur <= total:
            self.progress.emit(cur, total)

    def stop(self) -> None:
        self._aborted = True
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
