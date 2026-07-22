"""
后台工作线程 —— 在子进程中运行训练/推理/工具脚本，实时读取输出。
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from PySide6.QtCore import QThread, Signal

ROOT = Path(__file__).resolve().parent.parent


class _BaseWorker(QThread):
    """子进程工作线程基类。"""

    log_line = Signal(str)
    finished_ok = Signal()
    failed = Signal(str)
    stopped = Signal()

    def __init__(self, cmd: list[str]):
        super().__init__()
        self._cmd = cmd
        self._process: subprocess.Popen | None = None
        self._aborted = False

    def run(self) -> None:
        try:
            self._process = subprocess.Popen(
                self._cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(ROOT),
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
        except Exception as e:
            self.failed.emit(f"启动进程失败: {e}")
            return

        try:
            for line in self._process.stdout:
                stripped = line.rstrip("\n").rstrip("\r")
                if stripped:
                    self.log_line.emit(stripped)
                    self._on_line(stripped)
        except (IOError, OSError):
            pass

        self._process.wait()
        if self._aborted:
            self.stopped.emit()
        elif self._process.returncode == 0:
            self.finished_ok.emit()
        else:
            self.failed.emit(f"进程退出码: {self._process.returncode}")

    def _on_line(self, line: str) -> None:
        """子类可覆盖此方法来解析进度等。"""

    def stop(self) -> None:
        self._aborted = True
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()


class TrainWorker(_BaseWorker):
    """在子进程中运行训练脚本，解析 epoch 进度。"""

    progress = Signal(int)
    metrics_update = Signal(dict)

    def _on_line(self, line: str) -> None:
        self._parse_metrics_line(line)
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


class InferWorker(_BaseWorker):
    """在子进程中运行推理脚本，解析图片进度。"""

    progress = Signal(int, int)  # cur, total

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
