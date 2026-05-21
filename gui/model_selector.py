"""
Model selector dropdown with auto-download capability.
"""
from __future__ import annotations

import os
import urllib.request
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QStandardItem, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListView,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui.paths import MODEL_REGISTRY, PRETRAINED_DIR, get_model_download_url
from gui.styles import (
    COLOR_CARD_BG,
    COLOR_DISABLED,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    COMBO_STYLE,
    INPUT_RADIUS,
    PATH_COMBO_MIN_WIDTH,
    PROGRESS_HEIGHT,
    PROGRESS_STYLE,
)
from gui.widgets import btn, danger_btn


class _ModelDownloader(QThread):
    progress = Signal(int, int)
    finished = Signal(bool, str)
    error_msg = Signal(str)

    def __init__(self, filename: str, url: str, dest_dir: Path):
        super().__init__()
        self._filename = filename
        self._url = url
        self._dest = dest_dir / filename
        self._tmp = dest_dir / f"{filename}.tmp"
        self._aborted = False

    def run(self) -> None:
        try:
            self._dest.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(self._url) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(self._tmp, "wb") as f:
                    while True:
                        if self._aborted:
                            self._cleanup()
                            return
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total)
            if self._aborted:
                self._cleanup()
                return
            os.replace(str(self._tmp), str(self._dest))
            self.finished.emit(True, self._filename)
        except Exception as exc:
            self._cleanup()
            self.error_msg.emit(str(exc))
            self.finished.emit(False, self._filename)

    def stop(self) -> None:
        self._aborted = True

    def _cleanup(self) -> None:
        if self._tmp.is_file():
            self._tmp.unlink(missing_ok=True)


class ModelSelector(QWidget):
    model_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._model_states: dict[str, str] = {}
        self._downloader: _ModelDownloader | None = None
        self._custom_paths: list[str] = []
        self._status_timer: QTimer | None = None

        self._combo = QComboBox()
        self._combo.setMinimumWidth(320)
        self._combo.setStyleSheet(COMBO_STYLE)
        self._combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._combo.currentIndexChanged.connect(self._on_selection_changed)
        view = self._combo.view()
        view.setMinimumWidth(320)
        view.setResizeMode(QListView.Adjust)

        self._browse_btn = btn("浏览", primary=False)
        self._browse_btn.setFixedWidth(60)
        self._browse_btn.clicked.connect(self._on_browse)

        # ── download bar (hidden when idle) ──
        self._download_bar = QWidget()
        self._download_bar.setVisible(False)
        self._progress = QProgressBar()
        self._progress.setFixedHeight(PROGRESS_HEIGHT)
        self._progress.setStyleSheet(PROGRESS_STYLE)
        self._progress.setTextVisible(False)
        self._dl_status = QLabel("")
        self._dl_status.setStyleSheet(f"font-size:11px; color:{COLOR_TEXT_MUTED};")
        self._cancel_btn = danger_btn("取消下载")
        self._cancel_btn.clicked.connect(self._on_cancel_download)

        dl_row = QHBoxLayout(self._download_bar)
        dl_row.setContentsMargins(0, 0, 0, 0)
        dl_row.setSpacing(6)
        dl_row.addWidget(self._progress, 1)
        dl_row.addWidget(self._dl_status)
        dl_row.addWidget(self._cancel_btn)

        # ── main layout ──
        combo_row = QHBoxLayout()
        combo_row.setContentsMargins(0, 0, 0, 0)
        combo_row.setSpacing(6)
        combo_row.addWidget(self._combo, 1)
        combo_row.addWidget(self._browse_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(combo_row)
        layout.addWidget(self._download_bar)

        self._init_states()
        self._populate()

    # ── public API ──

    def current_model_path(self) -> str:
        idx = self._combo.currentIndex()
        if idx < 0:
            return ""
        data = self._combo.itemData(idx, Qt.UserRole)
        if not data or data == "__browse__":
            return ""
        if data in self._custom_paths or os.sep in data:
            return data
        p = PRETRAINED_DIR / data
        return str(p) if p.is_file() else data

    def set_model(self, name_or_path: str) -> None:
        if not name_or_path:
            return
        for fn, _display, _tag in MODEL_REGISTRY:
            if name_or_path == fn or name_or_path.endswith(f"/{fn}") or name_or_path.endswith(f"\\{fn}"):
                self._select_item_by_data(fn)
                return
        for fn, display, _tag in MODEL_REGISTRY:
            if name_or_path == display:
                self._select_item_by_data(fn)
                return
        p = Path(name_or_path)
        if p.is_file():
            if name_or_path not in self._custom_paths:
                self._custom_paths.append(name_or_path)
                if len(self._custom_paths) > 20:
                    self._custom_paths = self._custom_paths[-20:]
            self._populate()
            self._select_item_by_data(name_or_path)
            return
        for i in range(self._combo.count()):
            if self._combo.itemText(i) == name_or_path:
                self._combo.setCurrentIndex(i)
                return

    def add_custom_path(self, path: str) -> None:
        if path not in self._custom_paths:
            self._custom_paths.append(path)
            if len(self._custom_paths) > 20:
                self._custom_paths = self._custom_paths[-20:]
        self._populate()
        self._select_item_by_data(path)

    # ── internal ──

    def _init_states(self) -> None:
        for fn, _display, _tag in MODEL_REGISTRY:
            self._model_states[fn] = "ok" if (PRETRAINED_DIR / fn).is_file() else "missing"

    def _populate(self) -> None:
        self._combo.blockSignals(True)
        target_data = None
        if self._combo.currentIndex() >= 0:
            target_data = self._combo.itemData(self._combo.currentIndex(), Qt.UserRole)

        model = self._combo.model()
        model.clear()

        def _add(text: str, data: str | None, enabled: bool = True, color: str | None = None):
            item = QStandardItem(text)
            if data is not None:
                item.setData(data, Qt.UserRole)
            if not enabled:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            if color:
                item.setForeground(QColor(color))
            model.appendRow(item)

        # Group models by tag
        groups: dict[str, list[tuple[str, str, str]]] = {}
        for fn, display, tag in MODEL_REGISTRY:
            groups.setdefault(tag, []).append((fn, display, tag))

        group_labels = {
            "v8": "YOLOv8 分割",
            "v11": "YOLO11 分割",
            "v12": "YOLO12 分割",
        }

        seg_tags = ["v8", "v11", "v12"]
        det_tags = sorted(set(t for _, _, t in MODEL_REGISTRY) - set(seg_tags))

        for tag in seg_tags:
            if tag not in groups:
                continue
            display_models = [(fn, d, t) for fn, d, t in groups[tag] if fn.endswith("-seg.pt")]
            if not display_models:
                continue
            _add(f"── {group_labels.get(tag, tag)} ──", None, enabled=False, color=COLOR_DISABLED)
            for fn, display, _ in display_models:
                self._add_model_item(fn, display, _add)

        _add(f"── YOLOv8 检测 ──", None, enabled=False, color=COLOR_DISABLED)
        for fn, display, tag in groups.get("v8", []):
            if not fn.endswith("-seg.pt"):
                self._add_model_item(fn, display, _add)

        _add(f"── YOLO11 检测 ──", None, enabled=False, color=COLOR_DISABLED)
        for fn, display, tag in groups.get("v11", []):
            if not fn.endswith("-seg.pt"):
                self._add_model_item(fn, display, _add)

        # Separator + custom paths
        model.appendRow(QStandardItem(""))
        if self._custom_paths:
            _add("── 本地文件 ──", None, enabled=False, color=COLOR_DISABLED)
            for p in self._custom_paths:
                _add(Path(p).name, p, enabled=True)

        # Browse action
        model.appendRow(QStandardItem(""))
        _add("浏览本地文件...", "__browse__", enabled=True)

        # Restore or auto-select first downloaded
        if target_data and self._find_item_index(target_data) >= 0:
            self._combo.setCurrentIndex(self._find_item_index(target_data))
        else:
            for i in range(self._combo.count()):
                d = self._combo.itemData(i, Qt.UserRole)
                if d and self._model_states.get(d) == "ok":
                    self._combo.setCurrentIndex(i)
                    break

        self._combo.blockSignals(False)

    def _add_model_item(self, fn: str, display: str, _add_fn) -> None:
        state = self._model_states.get(fn, "missing")
        if state == "ok":
            _add_fn(f"{display}  ✓", fn, enabled=True)
        elif state == "downloading":
            _add_fn(f"{display}  (下载中...)", fn, enabled=True, color=COLOR_DISABLED)
        else:
            _add_fn(f"{display}  [点击下载]", fn, enabled=True, color=COLOR_DISABLED)

    def _find_item_index(self, data: str) -> int:
        for i in range(self._combo.count()):
            if self._combo.itemData(i, Qt.UserRole) == data:
                return i
        return -1

    def _select_item_by_data(self, data: str) -> None:
        idx = self._find_item_index(data)
        if idx >= 0:
            self._combo.setCurrentIndex(idx)

    # ── slots ──

    def _on_selection_changed(self, idx: int) -> None:
        if idx < 0:
            return
        data = self._combo.itemData(idx, Qt.UserRole)
        if not data:
            return
        if data == "__browse__":
            self._on_browse()
            return
        if data in self._custom_paths:
            self.model_changed.emit(data)
            return
        if data in self._model_states:
            state = self._model_states[data]
            if state == "ok":
                self.model_changed.emit(str(PRETRAINED_DIR / data))
            elif state == "missing":
                self._start_download(data)

    def _on_browse(self) -> None:
        f, _ = QFileDialog.getOpenFileName(
            self, "选择模型权重", "", "权重 (*.pt *.pth *.onnx);;所有文件 (*)"
        )
        if f:
            self.add_custom_path(f)
            self.model_changed.emit(f)

    def _start_download(self, filename: str) -> None:
        tag = None
        for fn, _display, t in MODEL_REGISTRY:
            if fn == filename:
                tag = t
                break
        if not tag:
            return

        self._model_states[filename] = "downloading"
        self._populate()

        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._cancel_btn.setVisible(True)
        self._dl_status.setText(f"正在下载 {filename} ...")
        self._download_bar.setVisible(True)
        self._combo.setEnabled(False)
        self._browse_btn.setEnabled(False)

        url = get_model_download_url(filename, tag)
        self._downloader = _ModelDownloader(filename, url, PRETRAINED_DIR)
        self._downloader.progress.connect(self._on_download_progress)
        self._downloader.finished.connect(self._on_download_finished)
        self._downloader.error_msg.connect(self._on_download_error)
        self._downloader.start()

    @Slot(int, int)
    def _on_download_progress(self, current: int, total: int) -> None:
        if total > 0:
            self._progress.setMaximum(total)
            self._progress.setValue(min(current, total))

    def _hide_download_bar(self, after_ms: int = 0) -> None:
        if after_ms > 0:
            if self._status_timer:
                self._status_timer.stop()
            self._status_timer = QTimer(self)
            self._status_timer.setSingleShot(True)
            self._status_timer.timeout.connect(lambda: self._download_bar.setVisible(False))
            self._status_timer.start(after_ms)
        else:
            self._download_bar.setVisible(False)

    @Slot(bool, str)
    def _on_download_finished(self, success: bool, filename: str) -> None:
        self._combo.setEnabled(True)
        self._browse_btn.setEnabled(True)

        if success:
            self._download_bar.setVisible(False)
            self._model_states[filename] = "ok"
            self._populate()
            self._select_item_by_data(filename)
            self.model_changed.emit(str(PRETRAINED_DIR / filename))
        else:
            self._model_states[filename] = "missing"
            self._dl_status.setText("下载失败")
            self._cancel_btn.setVisible(False)
            self._progress.setVisible(False)
            self._hide_download_bar(3000)
            self._populate()

    @Slot(str)
    def _on_download_error(self, msg: str) -> None:
        self._combo.setEnabled(True)
        self._browse_btn.setEnabled(True)
        self._dl_status.setText(f"下载出错: {msg}")
        self._cancel_btn.setVisible(False)
        self._progress.setVisible(False)
        self._hide_download_bar(5000)
        for fn, state in list(self._model_states.items()):
            if state == "downloading":
                self._model_states[fn] = "missing"
                break
        self._populate()

    def _on_cancel_download(self) -> None:
        if self._downloader and self._downloader.isRunning():
            self._downloader.stop()
        self._combo.setEnabled(True)
        self._browse_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        self._progress.setVisible(False)
        self._dl_status.setText("已取消下载")
        self._hide_download_bar(3000)
        for fn, state in list(self._model_states.items()):
            if state == "downloading":
                self._model_states[fn] = "missing"
                break
        self._populate()
