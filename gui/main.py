"""
YOLO 分割训练 / 推理桌面界面：与 scripts/train_segment.py、predict_test.py 能力对齐。
启动：在项目根目录执行  python gui/main.py
"""
from __future__ import annotations

import io
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import TrainConfig
from predict_test import InferConfig, YOLOInferencer
from train_segment import (
    execute_new_training,
    execute_resume_training,
    execute_train_from_previous_best,
    list_experiments,
)


class _TeeOut(io.TextIOBase):
    """把 stdout 同时写到原流并发出日志行（供训练线程使用）。"""

    def __init__(self, original, emit_fn):
        super().__init__()
        self._original = original
        self._emit = emit_fn

    def write(self, s: str) -> int:
        try:
            self._original.write(s)
        except Exception:
            pass
        if s and s.strip():
            for line in s.rstrip("\n").split("\n"):
                if line.strip():
                    self._emit(line)
        return len(s)

    def flush(self) -> None:
        try:
            self._original.flush()
        except Exception:
            pass


class TrainWorker(QThread):
    log_line = Signal(str)
    failed = Signal(str)
    finished_ok = Signal()

    def __init__(
        self,
        config: TrainConfig,
        mode: int,
        use_augment: bool,
        selected_exp: str | None = None,
    ):
        super().__init__()
        self._config = config
        self._mode = mode
        self._use_augment = use_augment
        self._selected_exp = selected_exp or ""

    def run(self) -> None:
        old = sys.stdout
        sys.stdout = _TeeOut(old, self.log_line.emit)
        try:
            if self._mode == 1:
                execute_new_training(self._config, self._use_augment)
            elif self._mode == 2:
                execute_resume_training(self._config)
            elif self._mode == 3:
                if not self._selected_exp:
                    raise ValueError("请先在列表中选择历史实验目录。")
                execute_train_from_previous_best(
                    self._config, self._selected_exp, self._use_augment
                )
            self.finished_ok.emit()
        except Exception as e:
            self.failed.emit(f"{e}\n{traceback.format_exc()}")
        finally:
            sys.stdout = old


class InferWorker(QThread):
    log_line = Signal(str)
    failed = Signal(str)
    finished_ok = Signal()

    def __init__(self, cfg: InferConfig):
        super().__init__()
        self._cfg = cfg

    def run(self) -> None:
        old = sys.stdout
        sys.stdout = _TeeOut(old, self.log_line.emit)
        try:
            YOLOInferencer(self._cfg).run()
            self.finished_ok.emit()
        except Exception as e:
            self.failed.emit(f"{e}\n{traceback.format_exc()}")
        finally:
            sys.stdout = old


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("YOLO Lab — 分割训练 / 推理")
        self.resize(920, 720)

        self._train_worker: TrainWorker | None = None
        self._infer_worker: InferWorker | None = None
        self._infer_defaults_done = False

        tabs = QTabWidget()
        tabs.addTab(self._build_train_tab(), "训练")
        tabs.addTab(self._build_infer_tab(), "推理")

        root = QVBoxLayout(self)
        root.addWidget(tabs)

        self._load_train_defaults()

    # --- 训练页 ---
    def _build_train_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        grp_paths = QGroupBox("路径")
        form_paths = QFormLayout(grp_paths)
        self.tr_data_yaml = QLineEdit()
        self.tr_model = QLineEdit()
        self.tr_results = QLineEdit()
        self.tr_logs = QLineEdit()
        form_paths.addRow("data.yaml", self._row_browse(self.tr_data_yaml, False, "YAML (*.yaml *.yml)"))
        form_paths.addRow("初始权重 .pt", self._row_browse(self.tr_model, False, "权重 (*.pt)"))
        form_paths.addRow("结果目录 outputs/results", self._row_browse(self.tr_results, True, None))
        form_paths.addRow("日志目录 outputs/logs", self._row_browse(self.tr_logs, True, None))
        layout.addWidget(grp_paths)

        grp_hp = QGroupBox("超参数")
        g = QGridLayout(grp_hp)
        self.tr_epochs = QSpinBox()
        self.tr_epochs.setRange(1, 100000)
        self.tr_imgsz = QSpinBox()
        self.tr_imgsz.setRange(32, 4096)
        self.tr_batch = QSpinBox()
        self.tr_batch.setRange(1, 1024)
        self.tr_device = QLineEdit()
        self.tr_exp = QLineEdit()
        g.addWidget(QLabel("epochs"), 0, 0)
        g.addWidget(self.tr_epochs, 0, 1)
        g.addWidget(QLabel("imgsz"), 0, 2)
        g.addWidget(self.tr_imgsz, 0, 3)
        g.addWidget(QLabel("batch"), 1, 0)
        g.addWidget(self.tr_batch, 1, 1)
        g.addWidget(QLabel("device"), 1, 2)
        g.addWidget(self.tr_device, 1, 3)
        g.addWidget(QLabel("实验名称"), 2, 0)
        g.addWidget(self.tr_exp, 2, 1, 1, 3)
        layout.addWidget(grp_hp)

        grp_mode = QGroupBox("训练模式（与 train_segment 一致）")
        mv = QVBoxLayout(grp_mode)
        self.rb_new = QRadioButton("1 — 新训练（从「初始权重」）")
        self.rb_resume = QRadioButton("2 — 续训（当前实验目录下的 last.pt）")
        self.rb_best = QRadioButton("3 — 从历史实验的 best.pt 再训")
        self.rb_new.setChecked(True)
        mv.addWidget(self.rb_new)
        mv.addWidget(self.rb_resume)
        mv.addWidget(self.rb_best)
        row_hist = QHBoxLayout()
        row_hist.addWidget(QLabel("历史实验（模式 3）:"))
        self.cb_history = QComboBox()
        self.cb_history.setMinimumWidth(400)
        row_hist.addWidget(self.cb_history, 1)
        btn_refresh = QPushButton("刷新列表")
        btn_refresh.clicked.connect(self._refresh_history)
        row_hist.addWidget(btn_refresh)
        mv.addLayout(row_hist)
        layout.addWidget(grp_mode)

        self.tr_augment = QCheckBox("启用数据增强（使用 config.py 中的增强参数）")
        self.tr_augment.setChecked(True)
        layout.addWidget(self.tr_augment)

        row_btn = QHBoxLayout()
        self.btn_start = QPushButton("开始训练")
        self.btn_start.clicked.connect(self._on_start_train)
        row_btn.addWidget(self.btn_start)
        layout.addLayout(row_btn)

        self.tr_log = QTextEdit()
        self.tr_log.setReadOnly(True)
        self.tr_log.setMinimumHeight(240)
        layout.addWidget(QLabel("输出"))
        layout.addWidget(self.tr_log)
        return w

    def _row_browse(self, edit: QLineEdit, directory: bool, filter_str: str | None):
        row = QHBoxLayout()
        row.addWidget(edit, 1)
        btn = QPushButton("浏览…")

        def browse():
            start = Path(edit.text().strip() or ROOT).resolve()
            if directory:
                d = QFileDialog.getExistingDirectory(self, "选择目录", str(start))
                if d:
                    edit.setText(d)
            else:
                f, _ = QFileDialog.getOpenFileName(
                    self,
                    "选择文件",
                    str(start),
                    filter_str or "所有文件 (*)",
                )
                if f:
                    edit.setText(f)

        btn.clicked.connect(browse)
        row.addWidget(btn)
        w = QWidget()
        w.setLayout(row)
        return w

    def _load_train_defaults(self) -> None:
        c = TrainConfig()
        self.tr_data_yaml.setText(c.data_yaml)
        self.tr_model.setText(c.model_file)
        self.tr_results.setText(c.results_dir)
        self.tr_logs.setText(c.log_dir)
        self.tr_epochs.setValue(int(c.epochs))
        self.tr_imgsz.setValue(int(c.imgsz))
        self.tr_batch.setValue(int(c.batch))
        self.tr_device.setText(str(c.device))
        self.tr_exp.setText(c.experiment_name)
        self.tr_augment.setChecked(bool(c.use_augment))
        self._refresh_history()

    def _refresh_history(self) -> None:
        self.cb_history.clear()
        res = Path(self.tr_results.text().strip() or ".")
        if not res.is_dir():
            return
        for name in sorted(list_experiments(str(res))):
            self.cb_history.addItem(name)

    def _build_config_from_train_ui(self) -> TrainConfig:
        c = TrainConfig()
        c.data_yaml = self.tr_data_yaml.text().strip()
        c.model_file = self.tr_model.text().strip()
        c.results_dir = self.tr_results.text().strip()
        c.log_dir = self.tr_logs.text().strip()
        c.epochs = int(self.tr_epochs.value())
        c.imgsz = int(self.tr_imgsz.value())
        c.batch = int(self.tr_batch.value())
        c.device = self.tr_device.text().strip() or "0"
        c.experiment_name = self.tr_exp.text().strip() or c.experiment_name
        c.use_augment = self.tr_augment.isChecked()
        return c

    @Slot()
    def _on_start_train(self) -> None:
        if self._train_worker and self._train_worker.isRunning():
            QMessageBox.warning(self, "提示", "训练正在进行中。")
            return

        cfg = self._build_config_from_train_ui()
        use_aug = self.tr_augment.isChecked()

        if self.rb_new.isChecked():
            mode = 1
            if not Path(cfg.model_file).is_file():
                QMessageBox.critical(self, "错误", f"找不到初始权重：\n{cfg.model_file}")
                return
            selected = None
            summary = f"模式1 新训练\n权重: {cfg.model_file}\ndata: {cfg.data_yaml}\n实验: {cfg.experiment_name}"
        elif self.rb_resume.isChecked():
            mode = 2
            if not Path(cfg.last_pt).is_file():
                r = QMessageBox.question(
                    self,
                    "未找到 last.pt",
                    f"未找到续训权重：\n{cfg.last_pt}\n\n是否改为「模式1 新训练」？",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if r != QMessageBox.Yes:
                    return
                mode = 1
                if not Path(cfg.model_file).is_file():
                    QMessageBox.critical(self, "错误", f"找不到初始权重：\n{cfg.model_file}")
                    return
            selected = None
            summary = f"模式2 续训\nlast.pt: {cfg.last_pt}" if mode == 2 else f"已改为模式1\n权重: {cfg.model_file}"
        else:
            mode = 3
            selected = self.cb_history.currentText().strip()
            if not selected:
                QMessageBox.warning(self, "提示", "请在「历史实验」下拉框中选择一项，或先刷新列表。")
                return
            best = Path(cfg.results_dir) / selected / "weights" / "best.pt"
            if not best.is_file():
                QMessageBox.critical(self, "错误", f"找不到：\n{best}")
                return
            summary = f"模式3 基于历史 best\n实验: {selected}\n{best}"

        r = QMessageBox.question(
            self,
            "确认训练",
            summary + f"\n\nepochs={cfg.epochs} imgsz={cfg.imgsz} batch={cfg.batch} device={cfg.device}\n数据增强={'开' if use_aug else '关'}\n\n是否开始？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if r != QMessageBox.Yes:
            return

        self.tr_log.clear()
        self.btn_start.setEnabled(False)

        self._train_worker = TrainWorker(cfg, mode, use_aug, selected if mode == 3 else None)
        self._train_worker.log_line.connect(self._append_train_log)
        self._train_worker.failed.connect(self._on_train_failed)
        self._train_worker.finished_ok.connect(self._on_train_done)
        self._train_worker.finished.connect(self._on_train_thread_finished)
        self._train_worker.start()

    @Slot(str)
    def _append_train_log(self, line: str) -> None:
        self.tr_log.append(line)

    @Slot(str)
    def _on_train_failed(self, msg: str) -> None:
        self.tr_log.append(msg)
        QMessageBox.critical(self, "训练失败", msg[:2000])

    @Slot()
    def _on_train_done(self) -> None:
        QMessageBox.information(self, "完成", "训练流程已结束（若 best.pt 存在，已尝试写入验证日志）。")
        self._refresh_history()

    @Slot()
    def _on_train_thread_finished(self) -> None:
        self.btn_start.setEnabled(True)

    # --- 推理页 ---
    def _build_infer_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        form = QFormLayout()
        self.ir_model = QLineEdit()
        self.ir_source = QLineEdit()
        self.ir_save = QLineEdit()
        self.ir_conf = QLineEdit("0.406")
        self.ir_imgsz = QSpinBox()
        self.ir_imgsz.setRange(32, 4096)
        self.ir_imgsz.setValue(640)
        form.addRow("模型 .pt", self._row_browse(self.ir_model, False, "权重 (*.pt)"))
        form.addRow("输入（图片目录或单张图）", self._row_browse(self.ir_source, True, None))
        form.addRow("保存目录", self._row_browse(self.ir_save, True, None))
        form.addRow("conf", self.ir_conf)
        form.addRow("imgsz", self.ir_imgsz)
        layout.addLayout(form)

        self.btn_infer = QPushButton("开始推理")
        self.btn_infer.clicked.connect(self._on_start_infer)
        layout.addWidget(self.btn_infer)

        self.ir_log = QTextEdit()
        self.ir_log.setReadOnly(True)
        self.ir_log.setMinimumHeight(200)
        layout.addWidget(self.ir_log)
        return w

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if self._infer_defaults_done:
            return
        self._infer_defaults_done = True
        from paths import BEST_SEG_MODEL, PREDICT_DIR, TEST_IMAGES_DIR

        self.ir_model.setText(BEST_SEG_MODEL)
        self.ir_source.setText(TEST_IMAGES_DIR)
        self.ir_save.setText(str(Path(PREDICT_DIR) / "predict_result"))

    @Slot()
    def _on_start_infer(self) -> None:
        if self._infer_worker and self._infer_worker.isRunning():
            QMessageBox.warning(self, "提示", "推理正在进行中。")
            return
        scripts_dir = SCRIPTS
        cfg = InferConfig(
            model_path=self.ir_model.text().strip(),
            source=self.ir_source.text().strip(),
            save_dir=self.ir_save.text().strip(),
            conf=float(self.ir_conf.text().strip() or "0.25"),
            imgsz=int(self.ir_imgsz.value()),
            task_param_file=str(scripts_dir / "infer_task_params.json"),
        )
        if not Path(cfg.model_path).is_file():
            QMessageBox.critical(self, "错误", f"找不到模型：\n{cfg.model_path}")
            return
        src = Path(cfg.source)
        if not src.exists():
            QMessageBox.critical(self, "错误", f"找不到输入：\n{cfg.source}")
            return

        self.ir_log.clear()
        self.btn_infer.setEnabled(False)
        self._infer_worker = InferWorker(cfg)
        self._infer_worker.log_line.connect(self.ir_log.append)
        self._infer_worker.failed.connect(self._on_infer_failed)
        self._infer_worker.finished_ok.connect(self._on_infer_done)
        self._infer_worker.finished.connect(self._on_infer_thread_finished)
        self._infer_worker.start()

    @Slot(str)
    def _on_infer_failed(self, msg: str) -> None:
        self.ir_log.append(msg)
        QMessageBox.critical(self, "推理失败", msg[:2000])

    @Slot()
    def _on_infer_done(self) -> None:
        QMessageBox.information(self, "完成", "推理已结束。")

    @Slot()
    def _on_infer_thread_finished(self) -> None:
        self.btn_infer.setEnabled(True)


def main() -> None:
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
