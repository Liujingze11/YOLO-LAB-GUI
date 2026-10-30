"""Small native extension around the original ISAT annotation window."""
from PyQt5 import QtCore, QtGui, QtWidgets


class ModelDevelopmentController(QtCore.QObject):
    def __init__(self, mainwindow):
        super().__init__(mainwindow)
        self.window = mainwindow
        self.widget = None
        self._annotation = True
        self._visible = {}
        self._shortcuts = {}
        self._viewport = None
        self._waiting_close = False
        self.stack = QtWidgets.QStackedWidget(mainwindow)
        self.annotation_view = mainwindow.takeCentralWidget()
        self.stack.addWidget(self.annotation_view)
        mainwindow.setCentralWidget(self.stack)
        self.navigation = QtWidgets.QToolBar('Workspace', mainwindow)
        self.navigation.setObjectName('isatModelDevelopmentNavigation')
        self.navigation.setMovable(False)
        self.navigation.setFloatable(False)
        self.navigation.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.navigation.setIconSize(QtCore.QSize(24, 24))
        self.navigation.toggleViewAction().setEnabled(False)
        group = QtWidgets.QActionGroup(self)
        group.setExclusive(True)
        self.annotation_action = self.navigation.addAction(mainwindow.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView), '数据标注')
        self.development_action = self.navigation.addAction(mainwindow.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon), '模型开发')
        for action in [self.annotation_action, self.development_action]:
            action.setCheckable(True); group.addAction(action)
        self.annotation_action.setChecked(True)
        self.annotation_action.triggered.connect(self.show_annotation)
        self.development_action.triggered.connect(self.show_development)
        mainwindow.addToolBar(QtCore.Qt.LeftToolBarArea, self.navigation)
        mainwindow.installEventFilter(self)
        self.retranslate()
        self._close_timer = QtCore.QTimer(self)
        self._close_timer.setInterval(100)
        self._close_timer.timeout.connect(self._finish_close)

    def retranslate(self):
        zh = self.window.cfg['software']['language'] == 'zh'
        self.annotation_action.setText('数据标注' if zh else 'Annotation')
        self.development_action.setText('模型开发' if zh else 'Model development')

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.LanguageChange:
            QtCore.QTimer.singleShot(0, self.retranslate)
        return False

    def show_development(self):
        if not self._annotation: return
        if self.widget is None:
            from .widget import ModelDevelopmentWidget
            self.widget = ModelDevelopmentWidget(self.window)
            self.widget.job_guard = self.authorize_job
            self.stack.addWidget(self.widget)
        view = self.window.view
        self._viewport = (QtGui.QTransform(view.transform()), view.mapToScene(view.viewport().rect().center()))
        widgets = [self.window.menuBar(), self.window.statusBar()]
        widgets += [w for w in self.window.findChildren(QtWidgets.QDockWidget) if w.parent() is self.window]
        widgets += [w for w in self.window.findChildren(QtWidgets.QToolBar) if w.parent() is self.window and w is not self.navigation]
        self._visible = {w: not w.isHidden() for w in widgets}
        # Remove only annotation keyboard bindings; async SAM action enablement stays intact.
        self._shortcuts = {a: a.shortcuts() for a in self.window.findChildren(QtWidgets.QAction) if a.shortcuts() and not self.widget.isAncestorOf(a.parent())}
        for action in self._shortcuts: action.setShortcuts([])
        for widget in widgets: widget.hide()
        self.stack.setCurrentWidget(self.widget)
        self._annotation = False
        self.development_action.setChecked(True)

    def show_annotation(self):
        if self._annotation: return
        self.stack.setCurrentWidget(self.annotation_view)
        for widget, visible in self._visible.items(): widget.setVisible(visible)
        for action, shortcuts in self._shortcuts.items(): action.setShortcuts(shortcuts)
        self._annotation = True
        self.annotation_action.setChecked(True)
        self._restore_viewport()
        QtCore.QTimer.singleShot(0, self._restore_viewport)
        self.window.view.setFocus()

    def _restore_viewport(self):
        if self._annotation and self._viewport:
            transform, center = self._viewport
            self.window.view.setTransform(transform)
            self.window.view.centerOn(center)

    def job_block_reason(self, device):
        if self._waiting_close: return '正在停止任务并退出，请稍候。'
        if str(device).lower() == 'cpu': return ''
        if self.widget:
            for tab, name in [(self.widget.train_tab, '_train_worker'), (self.widget.infer_tab, '_infer_worker'), (self.widget.export_tab, '_export_worker')]:
                worker = getattr(tab, name, None)
                if worker and worker.isRunning() and getattr(tab, '_job_device', 'cpu') != 'cpu':
                    return '已有 GPU 模型任务在运行。请先停止或等待它完成，也可选择 CPU。'
        sam = getattr(self.window, 'segany', None)
        if self.window.use_segment_anything and not self.window.use_remote_sam and sam and str(sam.device) != 'cpu':
            return 'SAM 正在使用 GPU。请先在 ISAT 模型管理中卸载 SAM，或选择 CPU 运行模型开发任务。'
        return ''

    def authorize_job(self, kind, device):
        reason = self.job_block_reason(device)
        if reason:
            QtWidgets.QMessageBox.warning(self.window, 'GPU 资源', reason)
            return False
        return True

    def confirm_close(self):
        if not self.widget or not self.widget.active_workers(): return True
        if not self._waiting_close:
            answer = QtWidgets.QMessageBox.question(self.window, '模型任务仍在运行', '停止正在运行的模型任务并退出？', QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            if answer != QtWidgets.QMessageBox.Yes: return False
            self._waiting_close = True
            self.widget.setEnabled(False)
            self.widget.stop_workers()
            self._close_timer.start()
        return False

    def _finish_close(self):
        if not self.widget.active_workers():
            self._close_timer.stop()
            self.widget.setEnabled(True)
            self._waiting_close = False
            self.window.close()


def install_model_development(mainwindow):
    return ModelDevelopmentController(mainwindow)
