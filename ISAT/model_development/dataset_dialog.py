"""Native dataset preparation with progress and cooperative cancellation."""
from datetime import datetime
from pathlib import Path
from PyQt5 import QtCore, QtWidgets
from .dataset import prepare_dataset, DatasetCancelled
from .paths import data_dir


class DatasetWorker(QtCore.QThread):
    completed = QtCore.pyqtSignal(dict)
    failed = QtCore.pyqtSignal(str)
    progress = QtCore.pyqtSignal(int, int, str)

    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.options = options
        self._cancelled = False

    def check_cancelled(self):
        if self._cancelled: raise DatasetCancelled('已取消，未发布数据集')

    def stop(self):
        self._cancelled = True

    def run(self):
        try:
            result = prepare_dataset(**self.options, check_cancelled=self.check_cancelled, progress=self.progress.emit)
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class DatasetDialog(QtWidgets.QDialog):
    dataset_ready = QtCore.pyqtSignal(dict)

    def __init__(self, image_root, label_root, categories, parent=None):
        super().__init__(parent)
        self.setWindowTitle('从当前 ISAT 标注准备训练集')
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.resize(640, 390)
        self.image_root, self.label_root, self.categories = image_root, label_root, list(categories)
        self.worker = None
        self._close_when_finished = False
        self.destination = QtWidgets.QLineEdit(str(data_dir()/'datasets'/datetime.now().strftime('dataset-%Y%m%d-%H%M%S')))
        self.ratio = QtWidgets.QDoubleSpinBox(); self.ratio.setRange(.01, .99); self.ratio.setSingleStep(.05); self.ratio.setValue(.2)
        self.seed = QtWidgets.QSpinBox(); self.seed.setRange(0, 2147483647); self.seed.setValue(42)
        self.ignore_background = QtWidgets.QCheckBox('忽略 __background__'); self.ignore_background.setChecked(True)
        self.keep_crowd = QtWidgets.QCheckBox('保留 crowd 目标'); self.keep_crowd.setChecked(True)
        form = QtWidgets.QFormLayout()
        for title, value in [('图片目录', image_root), ('标注目录', label_root)]:
            label = QtWidgets.QLabel(str(value)); label.setWordWrap(True); form.addRow(title, label)
        row = QtWidgets.QHBoxLayout(); row.addWidget(self.destination)
        browse = QtWidgets.QPushButton('浏览…'); browse.clicked.connect(self.browse); row.addWidget(browse)
        form.addRow('新的输出目录', row); form.addRow('验证集比例', self.ratio); form.addRow('随机种子', self.seed)
        form.addRow(self.ignore_background); form.addRow(self.keep_crowd)
        hint = QtWidgets.QLabel('仅使用已有 ISAT JSON 的图片，缺标注图片不作为负样本。复制图像并保留完整主档；YOLO 标签不包含备注、层级等全部信息。输出目录需为新目录，空间不足或取消时不发布数据集。')
        hint.setWordWrap(True)
        self.progress = QtWidgets.QProgressBar()
        self.status = QtWidgets.QLabel('就绪'); self.status.setWordWrap(True)
        self.start_button = QtWidgets.QPushButton('生成并用于训练'); self.start_button.clicked.connect(self.start)
        self.cancel_button = QtWidgets.QPushButton('取消'); self.cancel_button.clicked.connect(self.reject)
        actions = QtWidgets.QHBoxLayout(); actions.addStretch(); actions.addWidget(self.start_button); actions.addWidget(self.cancel_button)
        layout = QtWidgets.QVBoxLayout(self); layout.addLayout(form); layout.addWidget(hint); layout.addWidget(self.progress); layout.addWidget(self.status); layout.addLayout(actions)

    def browse(self):
        parent = QtWidgets.QFileDialog.getExistingDirectory(self, '选择输出的父目录')
        if parent: self.destination.setText(str(Path(parent)/datetime.now().strftime('dataset-%Y%m%d-%H%M%S')))

    def start(self):
        if self.worker and self.worker.isRunning(): return
        options = dict(image_root=self.image_root, label_root=self.label_root, destination=self.destination.text().strip(), categories=self.categories, val_ratio=self.ratio.value(), seed=self.seed.value(), ignore_background=self.ignore_background.isChecked(), keep_crowd=self.keep_crowd.isChecked())
        self.worker = DatasetWorker(options, self)
        self.worker.progress.connect(self.update_progress)
        self.worker.failed.connect(self.failed)
        self.worker.completed.connect(self.completed)
        self.worker.finished.connect(self.finished_worker)
        self.start_button.setEnabled(False); self.destination.setEnabled(False)
        self.status.setText('正在检查并生成独立数据集…')
        self.worker.start()

    def update_progress(self, current, total, name):
        self.progress.setRange(0, max(1, total)); self.progress.setValue(current); self.status.setText(name)

    def completed(self, result):
        self.status.setText(f"训练 {len(result['train'])} 张，验证 {len(result['val'])} 张，跳过缺标注 {len(result['skipped'])} 张")
        self.dataset_ready.emit(result)
        self.accept()

    def failed(self, message):
        self.status.setText(message)

    def finished_worker(self):
        self.start_button.setEnabled(True); self.destination.setEnabled(True)
        if self._close_when_finished: QtWidgets.QDialog.reject(self)

    def reject(self):
        if self.worker and self.worker.isRunning():
            self._close_when_finished = True; self.worker.stop(); self.status.setText('正在取消…')
        else: super().reject()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.reject(); event.ignore()
        else: event.accept()
