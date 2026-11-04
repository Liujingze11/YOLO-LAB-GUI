"""Small native extension around the original ISAT annotation window."""
from PyQt5 import QtCore, QtGui, QtWidgets
from ISAT.ui_theme import navigation_icon, apply_window_theme
from ISAT.workbench import WorkbenchFrame


class ModelDevelopmentController(QtCore.QObject):
    def __init__(self, mainwindow):
        super().__init__(mainwindow)
        self.window = mainwindow
        self.widget = None
        self.screening_widget = None
        self._annotation = True
        self._visible = {}
        self._shortcuts = {}
        self._viewport = None
        self._waiting_close = False
        self._dark = False
        self.stack = QtWidgets.QStackedWidget(mainwindow)
        self.annotation_view = self._create_annotation_workspace()
        self.stack.addWidget(self.annotation_view)
        self.frame = WorkbenchFrame(self.stack, mainwindow)
        mainwindow.setCentralWidget(self.frame)
        self.navigation = QtWidgets.QToolBar('Workspace', mainwindow)
        self.navigation.setObjectName('isatModelDevelopmentNavigation')
        self.navigation.setMovable(False)
        self.navigation.setFloatable(False)
        self.navigation.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.navigation.setIconSize(QtCore.QSize(24, 24))
        self.navigation.toggleViewAction().setEnabled(False)
        group = QtWidgets.QActionGroup(self)
        group.setExclusive(True)
        self.home_action = self.navigation.addAction(navigation_icon('home'), '返回首页')
        self.navigation.addSeparator()
        self.screening_action = self.navigation.addAction(navigation_icon('screening'), '数据筛选')
        self.annotation_action = self.navigation.addAction(navigation_icon('annotation'), '数据标注')
        self.development_action = self.navigation.addAction(navigation_icon('development'), '模型开发')
        for action in [self.screening_action, self.annotation_action, self.development_action]:
            action.setCheckable(True); group.addAction(action)
        self.annotation_action.setChecked(True)
        self.annotation_action.triggered.connect(self.show_annotation)
        self.screening_action.triggered.connect(self.show_screening)
        self.development_action.triggered.connect(self.show_development)
        mainwindow.addToolBar(QtCore.Qt.LeftToolBarArea, self.navigation)
        mainwindow.installEventFilter(self)
        self.retranslate()
        self._close_timer = QtCore.QTimer(self)
        self._close_timer.setInterval(100)
        self._close_timer.timeout.connect(self._finish_close)
        from ISAT.workspaces.integration import WorkspaceHomeController
        self.workspace_home = WorkspaceHomeController(self)
        self.stack.currentChanged.connect(self._update_frame)
        mainwindow.windowTitleChanged.connect(self._update_frame)
        self.home_action.triggered.connect(self.workspace_home.show_home)
        self.workspace_home.show_home()

    def _create_annotation_workspace(self):
        """Keep the original annotation layout inside its own workspace page."""
        window = self.window
        state = window.saveState()
        toolbars = [(bar, window.toolBarArea(bar))
                    for bar in window.findChildren(QtWidgets.QToolBar)
                    if bar.parent() is window]
        docks = [(dock, window.dockWidgetArea(dock))
                 for dock in window.findChildren(QtWidgets.QDockWidget)
                 if dock.parent() is window
                 and window.dockWidgetArea(dock) != QtCore.Qt.NoDockWidgetArea]
        page = QtWidgets.QMainWindow(window)
        page.setObjectName('isatAnnotationWorkspace')
        page.setWindowFlags(QtCore.Qt.Widget)
        page.setDockOptions(window.dockOptions())
        page.setCentralWidget(window.takeCentralWidget())

        # Reparent before installing so the outer window releases its chrome
        # without deleting the existing menus, status widgets or their actions.
        menu = window.menuWidget()
        menu.setParent(page)
        menu.setNativeMenuBar(False)
        page.setMenuBar(menu)
        status = window.statusBar()
        status.setParent(page)
        status.setSizeGripEnabled(False)
        page.setStatusBar(status)
        for toolbar, area in toolbars:
            window.removeToolBar(toolbar)
            page.addToolBar(area, toolbar)
        for dock, area in docks:
            window.removeDockWidget(dock)
            page.addDockWidget(area, dock)
        page.restoreState(state)
        return page

    def retranslate(self):
        zh = self.window.cfg['software']['language'] == 'zh'
        self.screening_action.setText('数据筛选' if zh else 'Data screening')
        self.annotation_action.setText('数据标注' if zh else 'Annotation')
        self.development_action.setText('模型开发' if zh else 'Model development')
        self.home_action.setText('返回首页' if zh else 'Home')
        if hasattr(self, 'workspace_home'): self._update_frame()

    def _update_frame(self, *_):
        page = self.stack.currentWidget()
        home = self.workspace_home
        action = (self.annotation_action if page is self.annotation_view else
                  self.development_action if self.widget is not None and page is self.widget else
                  self.screening_action)
        # Annotation uses the native window title for the current JSON path.
        # Keep project identity independent of that changing file title.
        project = home.current_root.name if home.current_root is not None else ''
        self.frame.set_page(action.text(), project,
                            str(home.current_root or ''), page is home.home)
        # The gallery has its own light presentation. Within a project every
        # work page, including lazily created ones, shares the selected theme.
        self._apply_workbench_theme()

    def _apply_workbench_theme(self):
        if not hasattr(self.window, '_glass_backdrop'): return
        dark = self._dark and self.stack.currentWidget() is not self.workspace_home.home
        if self.window.property('darkMode') != dark:
            apply_window_theme(self.window, dark)

    def _change_theme(self, dark):
        self._dark = dark
        self._apply_workbench_theme()

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.LanguageChange:
            QtCore.QTimer.singleShot(0, self.retranslate)
        return False

    def show_development(self):
        if self.widget is not None and self.stack.currentWidget() is self.widget: return
        if self.widget is None:
            try:
                import sys
                if sys.version_info < (3, 10): raise RuntimeError('Model development requires Python 3.10 or newer')
                from .widget import ModelDevelopmentWidget
                self.widget = ModelDevelopmentWidget(self.window, workspace_root=self.workspace_home.current_root)
            except (ImportError, RuntimeError) as exc:
                current_action = self.screening_action if self.screening_widget is not None and self.stack.currentWidget() is self.screening_widget else self.annotation_action
                current_action.setChecked(True)
                QtWidgets.QMessageBox.critical(self.window, 'Model development dependencies', '模型开发依赖未就绪，标注仍可使用。请检查当前解释器及 .[yolo] 依赖。\n'+str(exc))
                return False
            self.widget.job_guard = self.authorize_job
            self.widget.prepare_dataset_requested.connect(self.open_dataset_dialog)
            self.widget.release_sam_requested.connect(self.release_sam)
            self.widget.theme_changed.connect(self._change_theme)
            if self._dark: self.widget.set_dark_mode(True)
            self.workspace_home.configure_development(self.widget)
            self.stack.addWidget(self.widget)
        self._show_workspace(self.widget, self.development_action)

    def show_screening(self):
        if self.screening_widget is None:
            import copy
            from ISAT.data_screening.widget import DataScreeningWidget
            self.screening_widget = DataScreeningWidget(self.window)
            self.screening_widget.before_import = lambda: self._can_replace_annotation(False)
            self.screening_widget.before_save = self._can_save_screening
            self.screening_widget.category_provider = lambda: copy.deepcopy(self.window.cfg.get('label', []))
            self.screening_widget.project_ready.connect(self.open_screened_project)
            self.screening_widget.project_saved.connect(self._refresh_screened_annotation)
            self.workspace_home.configure_screening(self.screening_widget)
            self.stack.addWidget(self.screening_widget)
        self._show_workspace(self.screening_widget, self.screening_action)

    def _can_save_screening(self):
        from pathlib import Path
        page = self.screening_widget
        if not page or not page.session or not self.window.image_root: return True
        if Path(self.window.image_root).resolve() != page.session.root: return True
        if not self._can_replace_annotation(False): return False
        if not self.window.saved:
            QtWidgets.QMessageBox.warning(self.window, '未保存的标注', '请先在数据标注中保存当前标注，再保存同一项目的筛选修改。')
            return False
        return True

    def _refresh_screened_annotation(self, result):
        from pathlib import Path
        w = self.window
        if not w.image_root or Path(w.image_root).resolve() != Path(result['image_root']): return
        current = w.files_list[w.current_index] if 0 <= w.current_index < len(w.files_list) else None
        w.files_list = list(result['files'])
        w.current_index = w.files_list.index(current) if current in w.files_list else 0
        encoder = getattr(w, 'seganythread', None)
        if encoder is not None:
            encoder.results_dict.clear(); encoder.index = None
        if w.use_segment_anything_video and getattr(w, 'segany_video', None):
            w.segany_video.inference_state = {}
        self._viewport = None
        w.files_dock_widget.update_widget()
        w.show_image(w.current_index)

    def _show_workspace(self, page, action):
        self.navigation.show()
        if not self._annotation:
            self.stack.setCurrentWidget(page)
            action.setChecked(True)
            return
        view = self.window.view
        self._viewport = (QtGui.QTransform(view.transform()), view.mapToScene(view.viewport().rect().center()))
        widgets = [self.annotation_view.menuBar(), self.annotation_view.statusBar()]
        widgets += [w for w in self.annotation_view.findChildren(QtWidgets.QDockWidget) if w.parent() is self.annotation_view]
        widgets += [w for w in self.annotation_view.findChildren(QtWidgets.QToolBar) if w.parent() is self.annotation_view]
        self._visible = {w: not w.isHidden() for w in widgets}
        # Remove only annotation keyboard bindings; async SAM action enablement stays intact.
        pages = [p for p in (self.widget, self.screening_widget) if p is not None]
        self._shortcuts = {a: a.shortcuts() for a in self.window.findChildren(QtWidgets.QAction)
                           if a.shortcuts() and not any(isinstance(a.parent(), QtWidgets.QWidget)
                                                       and (a.parent() is p or p.isAncestorOf(a.parent())) for p in pages)}
        for annotation_action in self._shortcuts: annotation_action.setShortcuts([])
        for widget in widgets: widget.hide()
        self.stack.setCurrentWidget(page)
        self._annotation = False
        action.setChecked(True)

    def _can_replace_annotation(self, ask_unsaved=True):
        from ISAT.configs import STATUSMode
        w = self.window
        if self._waiting_close: return False
        for name in ('init_segany_thread', 'seganythread', 'segany_video_thread'):
            worker = getattr(w, name, None)
            if worker is not None and worker.isRunning():
                QtWidgets.QMessageBox.warning(w, '数据筛选', 'SAM 正在加载、编码或传播，请等待完成后再导入。')
                return False
        if w.scene.current_graph is not None and w.scene.mode in (STATUSMode.CREATE, STATUSMode.REPAINT):
            QtWidgets.QMessageBox.warning(w, '数据筛选', '请先完成或取消正在绘制的轮廓，再导入新项目。')
            return False
        if ask_unsaved and not w.saved:
            answer = QtWidgets.QMessageBox.question(w, '未保存的标注', '导入新项目之前，是否保存当前标注？',
                                                   QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
                                                   QtWidgets.QMessageBox.Save)
            if answer == QtWidgets.QMessageBox.Cancel: return False
            if answer == QtWidgets.QMessageBox.Save:
                w.save()
                if not w.saved: return False
        return True

    def open_screened_project(self, result):
        from pathlib import Path
        w = self.window
        images, labels = Path(result['image_root']), Path(result['label_root'])
        files = result['files']
        if not files or not labels.is_dir() or any(not (images / name).is_file() for name in files):
            QtWidgets.QMessageBox.warning(w, '数据筛选', '筛选项目文件已变化，请重新生成项目。')
            return False
        if not self._can_replace_annotation(): return False
        config = labels / 'isat.yaml'
        if not config.exists(): w.save_cfg(str(config))
        encoder = getattr(w, 'seganythread', None)
        if encoder is not None:
            encoder.results_dict.clear()
            encoder.index = None
        if w.use_segment_anything_video and getattr(w, 'segany_video', None):
            w.segany_video.inference_state = {}
        w.image_root, w.label_root = str(images), str(labels)
        w.config_file = str(config)
        w.reload_cfg()
        w.files_list = list(files)
        w.current_index = 0
        w.saved = True
        w.actionImages_dir.setStatusTip('Image root: ' + str(images))
        w.actionLabel_dir.setStatusTip('Label root: ' + str(labels))
        w.files_dock_widget.update_widget()
        self._viewport = None
        self.show_annotation()
        w.show_image(0)
        return True

    def show_annotation(self):
        self.navigation.show()
        from pathlib import Path
        page = self.screening_widget
        if (page and page._export_worker is not None and page.session and self.window.image_root
                and Path(self.window.image_root).resolve() == page.session.root):
            current = self.screening_action if self.stack.currentWidget() is page else self.development_action
            current.setChecked(True)
            QtWidgets.QMessageBox.warning(self.window, '正在保存筛选', '请等待副本保存完成，再进入同一项目的数据标注。')
            return
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

    def create_dataset_dialog(self):
        from .dataset_dialog import DatasetDialog
        from ISAT.configs import STATUSMode
        w = self.window
        if not w.image_root or not w.label_root:
            QtWidgets.QMessageBox.information(w, '准备训练数据', '请先在 ISAT 中打开图像目录和标注目录。')
            return None
        if w.scene.current_graph is not None and w.scene.mode in [STATUSMode.CREATE, STATUSMode.REPAINT]:
            QtWidgets.QMessageBox.warning(w, '准备训练数据', '请先完成或取消正在绘制的轮廓。')
            return None
        if not w.saved:
            w.save()
            if not w.saved: return None
        self.show_development()
        dialog = DatasetDialog(w.image_root, w.label_root, [c['name'] for c in w.cfg['label']], w)
        destination = self.workspace_home.dataset_destination()
        if destination is not None: dialog.destination.setText(str(destination))
        dialog.dataset_ready.connect(lambda result: self.widget.set_dataset(result['data_yaml']))
        self._dataset_dialog = dialog
        return dialog

    def open_dataset_dialog(self):
        dialog = self.create_dataset_dialog()
        if dialog: dialog.show()

    def release_sam(self):
        from ISAT.configs import STATUSMode
        w = self.window
        for name in ['init_segany_thread', 'seganythread', 'segany_video_thread']:
            thread = getattr(w, name, None)
            if thread is not None and thread.isRunning():
                QtWidgets.QMessageBox.warning(w, 'SAM', 'SAM 正在加载、编码或传播，请等待当前操作完成后释放。')
                return False
        if w.scene.current_graph is not None and w.scene.mode != STATUSMode.VIEW:
            QtWidgets.QMessageBox.warning(w, 'SAM', '请先完成或取消当前轮廓，再释放 SAM。')
            return False
        encoder = getattr(w, 'seganythread', None)
        if encoder is not None:
            encoder.results_dict.clear()
            encoder.index = None
        w.segany = None
        w.segany_video = None
        w.use_segment_anything = False
        w.use_segment_anything_video = False
        for name in ['actionSegment_anything_point', 'actionSegment_anything_box', 'actionVideo_segment', 'actionVideo_segment_once', 'actionVideo_segment_five_times']:
            getattr(w, name).setEnabled(False)
        w.model_manager_dialog.update_ui()
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available(): torch.cuda.empty_cache()
        w.labelGPUResource.setText('SAM unloaded')
        w.labelGPUResource.setToolTip('')
        return True

    def active_workers(self):
        workers = self.widget.active_workers() if self.widget else []
        if self.screening_widget: workers += self.screening_widget.active_workers()
        dialog = getattr(self, '_dataset_dialog', None)
        worker = getattr(dialog, 'worker', None)
        if worker is not None and worker.isRunning(): workers.append(worker)
        return workers

    def _gpu_task_running(self):
        if self.widget:
            for tab, name in [(self.widget.train_tab, '_train_worker'), (self.widget.infer_tab, '_infer_worker'), (self.widget.export_tab, '_export_worker')]:
                worker = getattr(tab, name, None)
                if worker and worker.isRunning() and getattr(tab, '_job_device', 'cpu') != 'cpu':
                    return True
        return False

    def authorize_sam_load(self):
        if self._gpu_task_running():
            QtWidgets.QMessageBox.warning(self.window, 'GPU 资源', 'GPU 模型开发任务正在运行，请先停止或等待完成后再加载 SAM。手工标注仍可继续。')
            return False
        return True

    def job_block_reason(self, device):
        if self._waiting_close: return '正在停止任务并退出，请稍候。'
        if str(device).lower() == 'cpu': return ''
        if self._gpu_task_running():
            return '已有 GPU 模型任务在运行。请先停止或等待它完成，也可选择 CPU。'
        sam = getattr(self.window, 'segany', None)
        # Remote encoding may still keep a decoder and prompt tensors on this GPU.
        if sam and str(sam.device) != 'cpu':
            return 'SAM 正在使用 GPU。请先点击顶部“释放 SAM 显存”，或选择 CPU 运行模型开发任务。'
        return ''

    def authorize_job(self, kind, device):
        reason = self.job_block_reason(device)
        if reason:
            QtWidgets.QMessageBox.warning(self.window, 'GPU 资源', reason)
            return False
        return True

    def confirm_close(self):
        if not self.active_workers():
            if self.screening_widget:
                if not self.screening_widget.confirm_leave(self.window.close): return False
                self.screening_widget.stop_workers()
            return True
        if not self._waiting_close:
            answer = QtWidgets.QMessageBox.question(self.window, '后台任务仍在运行', '停止正在运行的后台任务并退出？', QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            if answer != QtWidgets.QMessageBox.Yes: return False
            self._waiting_close = True
            if self.widget: self.widget.setEnabled(False)
            if self.screening_widget:
                self.screening_widget.setEnabled(False)
                self.screening_widget.stop_workers()
            for worker in self.active_workers():
                if hasattr(worker, 'stop'): worker.stop()
                elif hasattr(worker, 'cancel'): worker.cancel()
            self._close_timer.start()
        return False

    def _finish_close(self):
        if not self.active_workers():
            self._close_timer.stop()
            if self.widget: self.widget.setEnabled(True)
            if self.screening_widget: self.screening_widget.setEnabled(True)
            self._waiting_close = False
            self.window.close()


def install_model_development(mainwindow):
    return ModelDevelopmentController(mainwindow)
