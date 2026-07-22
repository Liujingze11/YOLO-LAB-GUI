"""
Real-time training curves — embedded matplotlib FigureCanvas in a QWidget.
"""
from __future__ import annotations

import time
from collections import deque

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

import matplotlib
matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

MAX_POINTS = 500  # keep at most N data points per curve
DRAW_INTERVAL_MS = 500  # throttle redraws


class TrainingChart(QWidget):
    """Real-time training metrics chart with loss and mAP subplots."""

    COLORS = {
        "box_loss": "#4da6ff",
        "seg_loss": "#50fa7b",
        "cls_loss": "#ffb86c",
        "dfl_loss": "#ff79c6",
        "mAP50": "#ff5555",
        "mAP50-95": "#f1fa8c",
    }

    def __init__(self, parent=None, dark_mode: bool = False):
        super().__init__(parent)
        self._dark = dark_mode
        self._epochs: list[int] = []
        self._data: dict[str, deque[tuple[int, float]]] = {
            "box_loss": deque(maxlen=MAX_POINTS),
            "seg_loss": deque(maxlen=MAX_POINTS),
            "cls_loss": deque(maxlen=MAX_POINTS),
            "dfl_loss": deque(maxlen=MAX_POINTS),
            "mAP50": deque(maxlen=MAX_POINTS),
            "mAP50-95": deque(maxlen=MAX_POINTS),
        }
        self._last_draw = 0.0

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(300, 240)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._fig = Figure(figsize=(5, 4), dpi=100)
        self._apply_bg_color()

        self._ax_loss = self._fig.add_subplot(211)
        self._ax_map = self._fig.add_subplot(212, sharex=self._ax_loss)

        self._init_axes()

        self._canvas = FigureCanvas(self._fig)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._canvas)

        self._fig.tight_layout(pad=2.0)

        # 节流重绘定时器
        self._draw_timer = QTimer(self)
        self._draw_timer.setInterval(DRAW_INTERVAL_MS)
        self._draw_timer.timeout.connect(self._do_redraw)
        self._draw_timer.start()

    def _apply_bg_color(self):
        """Apply dark/light background colors."""
        if self._dark:
            self._fig.patch.set_facecolor("#1e1e1e")
        else:
            self._fig.patch.set_facecolor("#fafafa")

    def _init_axes(self):
        """Configure both subplots with legends."""
        fg = "#e0e0e0" if self._dark else "#333333"
        grid_c = "#444" if self._dark else "#ddd"
        bg = "#2d2d2d" if self._dark else "#ffffff"

        for ax in (self._ax_loss, self._ax_map):
            ax.set_facecolor(bg)
            ax.tick_params(colors=fg, labelsize=8)
            ax.spines["bottom"].set_color(grid_c)
            ax.spines["left"].set_color(grid_c)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.grid(True, color=grid_c, linewidth=0.5, alpha=0.5)

        self._ax_loss.set_ylabel("Loss", color=fg, fontsize=9)
        self._ax_map.set_ylabel("mAP", color=fg, fontsize=9)
        self._ax_map.set_xlabel("Epoch", color=fg, fontsize=9)

        # 初始化空曲线
        self._lines: dict[str, object] = {}
        for key, color in self.COLORS.items():
            ax = self._ax_loss if "mAP" not in key else self._ax_map
            (line,) = ax.plot([], [], color=color, linewidth=1.2, label=key, alpha=0.85)
            self._lines[key] = line

        self._ax_loss.legend(
            loc="upper right", fontsize=7,
            facecolor=bg, edgecolor=grid_c,
            labelcolor=fg, framealpha=0.8,
        )
        self._ax_map.legend(
            loc="upper right", fontsize=7,
            facecolor=bg, edgecolor=grid_c,
            labelcolor=fg, framealpha=0.8,
        )

    def set_dark_mode(self, dark: bool):
        """Switch between dark and light theme."""
        self._dark = dark
        self._apply_bg_color()
        self._init_axes()
        self._do_redraw()

    def append_metrics(self, epoch: int, box_loss: float | None = None,
                       seg_loss: float | None = None, cls_loss: float | None = None,
                       dfl_loss: float | None = None, mAP50: float | None = None,
                       mAP50_95: float | None = None):
        """Add one epoch's metrics.  Only stores non-None values."""
        if box_loss is not None:
            self._data["box_loss"].append((epoch, box_loss))
        if seg_loss is not None:
            self._data["seg_loss"].append((epoch, seg_loss))
        if cls_loss is not None:
            self._data["cls_loss"].append((epoch, cls_loss))
        if dfl_loss is not None:
            self._data["dfl_loss"].append((epoch, dfl_loss))
        if mAP50 is not None:
            self._data["mAP50"].append((epoch, mAP50))
        if mAP50_95 is not None:
            self._data["mAP50-95"].append((epoch, mAP50_95))

    def _do_redraw(self):
        """Throttled redraw: update line data and refresh canvas."""
        now = time.monotonic()
        if now - self._last_draw < DRAW_INTERVAL_MS / 1500:
            return
        self._last_draw = now

        for key, line in self._lines.items():
            points = self._data[key]
            if points:
                xs, ys = zip(*points)
                line.set_data(xs, ys)
            else:
                line.set_data([], [])

        # 调整子图范围
        for ax in (self._ax_loss, self._ax_map):
            ax.relim()
            ax.autoscale_view(scalex=True, scaley=True)

        self._canvas.draw_idle()

    def reset(self):
        """Clear all data and reset chart."""
        for key in self._data:
            self._data[key].clear()
        for line in self._lines.values():
            line.set_data([], [])
        for ax in (self._ax_loss, self._ax_map):
            ax.relim()
            ax.autoscale_view()
        self._canvas.draw_idle()

    def closeEvent(self, event):
        self._draw_timer.stop()
        super().closeEvent(event)
