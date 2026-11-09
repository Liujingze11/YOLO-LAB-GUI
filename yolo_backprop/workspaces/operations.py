"""Cancelable modal progress for filesystem work; the GUI event loop stays responsive."""
from PyQt5 import QtCore, QtWidgets
from yolo_backprop.data_screening.workers import BackgroundWorker, Cancelled


class OperationWorker(BackgroundWorker):
    def __init__(self, operation, parent=None):
        super().__init__(parent)
        self.operation = operation
        self.result = None
        self.error = None
        self.cancelled = False

    def run(self):
        try:
            self.result = self.operation(self.check_cancelled, self.progress.emit)
            self.check_cancelled()
        except Cancelled:
            self.cancelled = True
        except Exception as exc:
            self.error = exc


class OperationDialog(QtWidgets.QDialog):
    def __init__(self, parent, title, operation):
        super().__init__(parent)
        self.setWindowTitle(title); self.resize(480, 180)
        self.worker = OperationWorker(operation, self)
        layout = QtWidgets.QVBoxLayout(self); layout.setContentsMargins(24, 20, 24, 20)
        self.message = QtWidgets.QLabel(title); self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.progress = QtWidgets.QProgressBar(); self.progress.setRange(0, 0)
        layout.addWidget(self.progress)
        self.cancel_button = QtWidgets.QPushButton('取消')
        self.cancel_button.clicked.connect(self.reject)
        row = QtWidgets.QHBoxLayout(); row.addStretch(); row.addWidget(self.cancel_button)
        layout.addLayout(row)
        self.worker.progress.connect(self._progress)
        self.worker.finished.connect(self.accept)

    def _progress(self, current, total, name):
        if not self.cancel_button.isEnabled(): return
        self.progress.setRange(0, max(1, total)); self.progress.setValue(current)
        self.message.setText(self.windowTitle() + '\n' + name)

    def reject(self):
        if self.worker.isRunning():
            self.worker.stop(); self.cancel_button.setEnabled(False)
            self.message.setText('正在取消并清理临时文件…')
        else: super().reject()

    def closeEvent(self, event):
        if self.worker.isRunning(): self.reject(); event.ignore()
        else: super().closeEvent(event)


def run_operation(parent, title, operation):
    dialog = OperationDialog(parent, title, operation)
    dialog.worker.start()
    dialog.exec_()
    dialog.worker.wait()
    result, error = dialog.worker.result, dialog.worker.error
    cancelled = dialog.worker.cancelled or not dialog.cancel_button.isEnabled()
    dialog.deleteLater()
    if error is not None: raise error
    return None if cancelled else result


def inspect_project(store, root, check_cancelled=lambda: None):
    root = store._checked_root(root)
    before = root.stat()
    info = store.read_existing(root, check_cancelled)
    check_cancelled()
    after = root.stat()
    identity = (before.st_dev, before.st_ino)
    if identity != (after.st_dev, after.st_ino):
        raise ValueError('识别期间项目目录发生变化，请重新打开。')
    info['_source_identity'] = identity
    return info
