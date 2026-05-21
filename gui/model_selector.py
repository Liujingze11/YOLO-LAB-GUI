"""
Model selector dropdown with auto-download capability.
"""
from __future__ import annotations

import os
import urllib.request
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QStandardItem, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
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
    COLOR_DISABLED,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    COMBO_STYLE,
    PROGRESS_STYLE,
)
from gui.i18n import tr
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


class DownloadDialog(QDialog):
    """Modal dialog showing download progress with cancel button."""

    def __init__(self, filename: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._filename = filename
        self._cancelled = False
        self.setWindowTitle(tr("model.dialog.title"))
        self.setFixedSize(440, 130)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        self._label = QLabel(tr("model.dialog.downloading", filename=filename))
        self._label.setProperty("themeClass", "field_label")
        self._label.setStyleSheet(f"font-size: 13px; color: {COLOR_TEXT};")
        layout.addWidget(self._label)

        self._progress = QProgressBar()
        self._progress.setFixedHeight(14)
        self._progress.setProperty("themeClass", "progress")
        self._progress.setStyleSheet(PROGRESS_STYLE)
        self._progress.setTextVisible(False)
        layout.addWidget(self._progress)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self._status = QLabel("")
        self._status.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_MUTED};")
        btn_row.addWidget(self._status, 1)
        self._cancel_btn = danger_btn(tr("model.dialog.cancel_btn"))
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._cancel_btn)
        layout.addLayout(btn_row)

    def set_progress(self, current: int, total: int) -> None:
        if total > 0:
            self._progress.setMaximum(total)
            self._progress.setValue(min(current, total))
            pct = current * 100 // total if total else 0
            self._status.setText(f"{current // 1048576}MB / {total // 1048576}MB  ({pct}%)")

    def set_error(self, msg: str) -> None:
        self._label.setText(tr("model.dialog.failed", filename=self._filename))
        self._status.setText(msg[:80])

    def set_cancelled(self) -> None:
        self._label.setText(tr("model.dialog.cancelled"))
        self._status.setText(self._filename)

    def _on_cancel(self) -> None:
        self._cancelled = True
        self.reject()

    @property
    def cancelled(self) -> bool:
        return self._cancelled


class ModelSelector(QWidget):
    model_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._model_states: dict[str, str] = {}
        self._downloader: _ModelDownloader | None = None
        self._custom_paths: list[str] = []
        self._download_dialog: DownloadDialog | None = None

        self._combo = QComboBox()
        self._combo.setMinimumWidth(320)
        self._combo.setProperty("themeClass", "combo")
        self._combo.setStyleSheet(COMBO_STYLE)
        self._combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._combo.currentIndexChanged.connect(self._on_selection_changed)
        view = self._combo.view()
        view.setMinimumWidth(320)
        view.setResizeMode(QListView.Adjust)

        self._browse_btn = btn("浏览", primary=False, i18n_key="train.btn.browse")
        self._browse_btn.setFixedWidth(60)
        self._browse_btn.clicked.connect(self._on_browse)

        combo_row = QHBoxLayout()
        combo_row.setContentsMargins(0, 0, 0, 0)
        combo_row.setSpacing(6)
        combo_row.addWidget(self._combo, 1)
        combo_row.addWidget(self._browse_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(combo_row)

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

        groups: dict[str, list[tuple[str, str, str]]] = {}
        for fn, display, tag in MODEL_REGISTRY:
            groups.setdefault(tag, []).append((fn, display, tag))

        seg_keys = {
            "v8": "model.group.v8_seg",
            "v11": "model.group.v11_seg",
            "v12": "model.group.v12_seg",
        }

        seg_tags = ["v8", "v11", "v12"]

        for tag in seg_tags:
            if tag not in groups:
                continue
            display_models = [(fn, d, t) for fn, d, t in groups[tag] if fn.endswith("-seg.pt")]
            if not display_models:
                continue
            _add(f"── {tr(seg_keys.get(tag, tag))} ──", None, enabled=False, color=COLOR_DISABLED)
            for fn, display, _ in display_models:
                self._add_model_item(fn, display, _add)

        _add(f"── {tr('model.group.v8_det')} ──", None, enabled=False, color=COLOR_DISABLED)
        for fn, display, tag in groups.get("v8", []):
            if not fn.endswith("-seg.pt"):
                self._add_model_item(fn, display, _add)

        _add(f"── {tr('model.group.v11_det')} ──", None, enabled=False, color=COLOR_DISABLED)
        for fn, display, tag in groups.get("v11", []):
            if not fn.endswith("-seg.pt"):
                self._add_model_item(fn, display, _add)

        model.appendRow(QStandardItem(""))
        if self._custom_paths:
            _add(f"── {tr('model.group.local')} ──", None, enabled=False, color=COLOR_DISABLED)
            for p in self._custom_paths:
                _add(Path(p).name, p, enabled=True)

        model.appendRow(QStandardItem(""))
        _add(tr("model.action.browse"), "__browse__", enabled=True)

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
            _add_fn(f"{display}  {tr('model.tag.downloading')}", fn, enabled=True, color=COLOR_DISABLED)
        else:
            _add_fn(f"{display}  {tr('model.tag.download')}", fn, enabled=True, color=COLOR_DISABLED)

    def _find_item_index(self, data: str) -> int:
        for i in range(self._combo.count()):
            if self._combo.itemData(i, Qt.UserRole) == data:
                return i
        return -1

    def _select_item_by_data(self, data: str) -> None:
        idx = self._find_item_index(data)
        if idx >= 0:
            self._combo.setCurrentIndex(idx)

    def _select_first_ok(self) -> None:
        """Move combo selection to the first available 'ok' model."""
        for i in range(self._combo.count()):
            d = self._combo.itemData(i, Qt.UserRole)
            if d and self._model_states.get(d) == "ok":
                self._combo.setCurrentIndex(i)
                return

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

        url = get_model_download_url(filename, tag)
        self._downloader = _ModelDownloader(filename, url, PRETRAINED_DIR)
        self._downloader.progress.connect(self._on_download_progress)
        self._downloader.finished.connect(self._on_download_finished)
        self._downloader.error_msg.connect(self._on_download_error)

        self._download_dialog = DownloadDialog(filename, self.window())
        self._download_dialog.rejected.connect(self._on_dialog_closed)
        self._download_dialog.show()

        self._combo.setEnabled(False)
        self._browse_btn.setEnabled(False)
        self._downloader.start()

    @Slot(int, int)
    def _on_download_progress(self, current: int, total: int) -> None:
        if self._download_dialog:
            self._download_dialog.set_progress(current, total)

    @Slot()
    def _on_dialog_closed(self) -> None:
        if self._download_dialog is None:
            return
        cancelled = self._download_dialog.cancelled
        if cancelled and self._downloader and self._downloader.isRunning():
            self._downloader.stop()
        self._combo.setEnabled(True)
        self._browse_btn.setEnabled(True)
        for fn, state in list(self._model_states.items()):
            if state == "downloading":
                self._model_states[fn] = "missing"
                break
        self._populate()
        self._select_first_ok()
        self._download_dialog = None

    @Slot(bool, str)
    def _on_download_finished(self, success: bool, filename: str) -> None:
        self._combo.setEnabled(True)
        self._browse_btn.setEnabled(True)

        if success:
            if self._download_dialog:
                self._download_dialog.accept()
                self._download_dialog = None
            self._model_states[filename] = "ok"
            self._populate()
            self._select_item_by_data(filename)
            self.model_changed.emit(str(PRETRAINED_DIR / filename))
        else:
            # Dialog stays open to show the error; user closes it manually.
            self._model_states[filename] = "missing"
            self._populate()
            self._select_first_ok()

    @Slot(str)
    def _on_download_error(self, msg: str) -> None:
        self._combo.setEnabled(True)
        self._browse_btn.setEnabled(True)
        if self._download_dialog:
            self._download_dialog.set_error(msg)
            self._download_dialog._cancel_btn.setText(tr("model.dialog.close_btn"))
            try:
                self._download_dialog._cancel_btn.clicked.disconnect()
            except Exception:
                pass
            self._download_dialog._cancel_btn.clicked.connect(self._download_dialog.reject)
        for fn, state in list(self._model_states.items()):
            if state == "downloading":
                self._model_states[fn] = "missing"
                break
        self._populate()
        self._select_first_ok()
