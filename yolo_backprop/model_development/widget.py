"""Six model development pages for the YOLO-BACKPROP PyQt5 workbench."""
from PyQt5 import QtCore, QtGui, QtWidgets
from .gui.i18n import tr, set_language, apply_language, AVAILABLE_LANGS
from .gui.styles import apply_theme_to_widgets, TAB_WIDGET_STYLE
from yolo_backprop.ui_theme import page_style
from .gui.tabs.train_tab import TrainTab
from .gui.tabs.infer_tab import InferTab
from .gui.tabs.export_tab import ExportTab
from .gui.tabs.logs_tab import LogsTab
from .gui.tabs.tools_tab import ToolsTab
from .gui.tabs.settings_tab import SettingsTab


class ModelDevelopmentWidget(QtWidgets.QWidget):
    prepare_dataset_requested = QtCore.pyqtSignal()
    release_sam_requested = QtCore.pyqtSignal()
    theme_changed = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None, workspace_root=None):
        super().__init__(parent)
        self.setObjectName('ModelDevelopment')
        self.setFont(QtGui.QFont('Noto Sans CJK SC', 10))
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet(page_style('ModelDevelopment'))
        self._dark = False
        self.job_guard = lambda kind, device: True
        history = {}
        self.tabs = QtWidgets.QTabWidget(self)
        self.tabs.setProperty('themeClass', 'tab_widget')
        self.tabs.setProperty('i18nKey', 'tabs')
        self.tabs.setStyleSheet(TAB_WIDGET_STYLE)
        self.train_tab = TrainTab(path_history=history)
        self.infer_tab = InferTab(path_history=history)
        self.export_tab = ExportTab(path_history=history)
        self.logs_tab = LogsTab(path_history=history, workspace_root=workspace_root)
        self.tools_tab = ToolsTab(path_history=history)
        self.settings_tab = SettingsTab()
        for page in [self.train_tab, self.infer_tab, self.export_tab]:
            page.before_job = self.authorize_job
        self.settings_tab.reset_splitter_requested.connect(self.train_tab.reset_splitter)
        for widget, key in [(self.train_tab, 'tab.train'), (self.infer_tab, 'tab.infer'), (self.export_tab, 'tab.export'), (self.logs_tab, 'tab.logs'), (self.tools_tab, 'tab.tools'), (self.settings_tab, 'tab.settings')]:
            index = self.tabs.addTab(widget, tr(key))
            self.tabs.tabBar().setTabData(index, key)
        self.prepare_button = QtWidgets.QPushButton('从当前标注准备训练集…')
        self.prepare_button.clicked.connect(self.prepare_dataset_requested)
        self._language = QtWidgets.QComboBox()
        for code, label in AVAILABLE_LANGS.items(): self._language.addItem(label, code)
        self._language.currentIndexChanged.connect(self._change_language)
        theme = QtWidgets.QPushButton('☀ / ☾')
        theme.setMaximumWidth(60)
        theme.clicked.connect(self._change_theme)
        self.command_bar = QtWidgets.QFrame()
        self.command_bar.setProperty('glassRole', 'commandBar')
        toolbar = QtWidgets.QHBoxLayout(self.command_bar)
        toolbar.setContentsMargins(12, 8, 12, 8); toolbar.setSpacing(8)
        toolbar.addWidget(self.prepare_button)
        release = QtWidgets.QPushButton('释放 SAM 显存')
        release.clicked.connect(self.release_sam_requested)
        toolbar.addWidget(release)
        toolbar.addStretch()
        toolbar.addWidget(self._language)
        toolbar.addWidget(theme)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.command_bar)
        layout.addWidget(self.tabs)
        self._start_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence('Ctrl+Return'), self)
        self._start_shortcut.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self._start_shortcut.activated.connect(self._start_current)
        from yolo_backprop.shortcuts import development_settings
        self.apply_shortcuts(development_settings().bindings)

    def apply_shortcuts(self, bindings):
        self._start_shortcut.setKey(QtGui.QKeySequence(bindings['run']))

    def authorize_job(self, kind, device):
        return self.job_guard(kind, device)

    def _change_language(self, index):
        set_language(self._language.itemData(index)); apply_language(self)
        self.prepare_button.setText('从当前标注准备训练集…' if self._language.itemData(index) == 'zh' else 'Prepare dataset from annotations…')

    def _change_theme(self):
        self.set_dark_mode(not self._dark)

    def set_dark_mode(self, dark):
        self._dark = dark
        apply_theme_to_widgets(self, self._dark)
        self.train_tab.set_dark_mode(self._dark)
        self.setStyleSheet(page_style('ModelDevelopment', self._dark))
        self.theme_changed.emit(dark)

    def _start_current(self):
        if self.tabs.currentIndex() == 0: self.train_tab._on_start_train()
        elif self.tabs.currentIndex() == 1: self.infer_tab._on_start_infer()

    def active_workers(self):
        workers = []
        for obj in self.findChildren(QtCore.QObject):
            for attr in ['_train_worker', '_infer_worker', '_export_worker', '_tool_worker', '_gpu_worker', '_gpu_install_worker', '_downloader']:
                worker = getattr(obj, attr, None)
                if worker is not None and worker.isRunning() and worker not in workers: workers.append(worker)
        return workers

    def stop_workers(self):
        for worker in self.active_workers():
            if hasattr(worker, 'stop'): worker.stop()
            elif hasattr(worker, 'cancel'): worker.cancel()

    def set_dataset(self, path):
        self.train_tab.tr_data_yaml.setCurrentText(str(path))
        self.train_tab._update_dataset_info()
        self.tabs.setCurrentIndex(0)

    def closeEvent(self, event):
        self.stop_workers()
        super().closeEvent(event)
