"""Connect the launch gallery to the existing native annotation workbench."""
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from PyQt5 import QtCore, QtWidgets
import yaml

from yolo_backprop.data_screening.workspace import WorkspaceSettings
from .home import WorkspaceHome
from .store import WorkspaceStore, training_image


class WorkspaceHomeController(QtCore.QObject):
    def __init__(self, controller):
        super().__init__(controller)
        self.controller = controller
        self.window = controller.window
        self._default_config_file = self.window.config_file
        self.store = WorkspaceStore()
        self.store.prune_unsafe_locations()
        self.current_root = None
        self.storage_root = None
        self._current_identity = None
        self._resume_page = None
        self._restore_annotation = False
        self.home = WorkspaceHome(self.store)
        self.home.workspace_requested.connect(self.open_workspace)
        self.home.location_ready.connect(lambda info: self.open_workspace(info['root'], info))
        self.home.delete_requested.connect(self.delete_workspace)
        self.home.remove_requested.connect(self.remove_workspace)
        controller.stack.addWidget(self.home)

    def show_home(self):
        c = self.controller
        if c.stack.currentWidget() is not self.home:
            self._resume_page = c.stack.currentWidget()
        if not self.save_current(): return
        self.home.refresh()
        c._show_workspace(self.home, c.home_action)
        c.navigation.hide()
        self.window.setWindowTitle('YOLO-BACKPROP')

    def _error(self, message):
        QtWidgets.QMessageBox.warning(self.window, '工作空间', str(message))

    @staticmethod
    def _directory_identity(root):
        if root.is_symlink() or not root.is_dir(): raise ValueError('项目目录不可用，请重新选择。')
        stat = root.stat()
        return stat.st_dev, stat.st_ino

    def _same_current_directory(self):
        try: return self._directory_identity(self.current_root) == self._current_identity
        except (OSError, ValueError, AttributeError): return False

    def save_current(self):
        if self.current_root is None: return True
        if not self._same_current_directory() or not self.store.has_metadata(self.current_root):
            self.window.config_file = self._default_config_file
            return True
        c = self.controller
        try:
            state = self.store.read(self.current_root)['state']
            if c.widget is not None:
                state['training'] = c.widget.train_tab._get_current_config_dict()
            page = c.screening_widget
            if page and page.session and page.session.project_root.parent == self.storage_root / 'projects':
                state['project_name'] = page.session.project_root.name
            if c.stack.currentWidget() is not self.home:
                state['page'] = ('annotation' if c._annotation else
                                 'development' if c.stack.currentWidget() is c.widget else 'screening')
            state['annotation_index'] = self.window.current_index or 0
            self.store.update(self.current_root, state=state)
            return True
        except (OSError, ValueError, TypeError) as exc:
            self._error('无法保存工作空间记录：' + str(exc)); return False

    def open_workspace(self, root, detected=None):
        c = self.controller
        try:
            if detected is not None:
                info = detected
            elif self.store.has_metadata(root):
                info = self.store.read(root)
            else:
                from .operations import run_operation, inspect_project
                info = run_operation(self.home, '正在自动识别项目…',
                                     lambda check, progress: inspect_project(self.store, root, check))
                if info is None: return False
            root = Path(info['root'])
            identity = self._directory_identity(root)
            if '_source_identity' in info and identity != tuple(info['_source_identity']):
                raise ValueError('识别后项目目录发生变化，请重新打开。')
        except (OSError, ValueError) as exc:
            self._error(exc); return False
        if root == self.current_root and identity == self._current_identity:
            self._resume()
            return True
        if self._has_pending_tasks():
            self._error('当前工作空间仍有后台任务，请结束任务后再切换工作空间。')
            return False
        if c.screening_widget and not c.screening_widget.confirm_leave(lambda: self.open_workspace(root)):
            return False
        if not c._can_replace_annotation(): return False
        if not self.save_current(): return False
        try:
            if info.get('source_kind') == 'yolo':
                from .operations import run_operation
                from .organize import organize_yolo
                organized = run_operation(self.home, '已识别 YOLO 数据集，正在整理工作副本…',
                                          lambda check, progress: organize_yolo(info, check, progress))
                if organized is None: return False
                info = dict(info, organized_dataset_yaml=organized)
            if self._directory_identity(root) != identity:
                raise ValueError('项目目录已发生变化，请重新选择；未修改原文件。')
            self.store.register(root, info)
            storage = Path(info['storage_root'])
            WorkspaceSettings().select(storage)
            config = storage / '.yolo-backprop' / 'isat.yaml'
            if config.parent.is_symlink(): raise ValueError('工作空间缓存目录不能是符号链接')
            config.parent.mkdir(exist_ok=True)
            if not config.exists():
                config.write_text(yaml.safe_dump({'label': self.window.cfg.get('label', [])}, allow_unicode=True), encoding='utf-8')
        except (OSError, ValueError) as exc:
            self._error(exc); return False
        self._reset_workbench()
        self.current_root = root
        self.storage_root = storage
        self._current_identity = identity
        self._resume_page = None
        self._restore_annotation = False
        self.window.config_file = str(config)
        self.window.reload_cfg()
        self.window.setWindowTitle(info['name'] + ' · YOLO-BACKPROP')
        c.show_screening()
        kind = {'images': '图片', 'isat': '图像标注', 'yolo': 'YOLO 数据集'}.get(info.get('source_kind'))
        c.screening_widget.source_description = '自动识别：' + kind if kind else ''
        state = info['state']
        name = state.get('project_name')
        projects = c.screening_widget.workspace.projects()
        recent = next((p for p in projects if p.name == name), None)
        if recent is None and info['external'] and projects:
            recent = projects[0]
        if recent is not None:
            self._restore_annotation = state.get('page') == 'annotation'
            c.screening_widget.open_folder(str(recent), project=True)
        elif info['external'] and info.get('source_kind') != 'yolo':
            c.screening_widget.open_folder(info['source_images'])
        if state.get('page') == 'development' or (info['external'] and info.get('source_kind') == 'yolo'):
            c.show_development()
        return True

    def _has_pending_tasks(self):
        c = self.controller
        dialog = getattr(c, '_dataset_dialog', None)
        return bool(c.active_workers() or c._waiting_close
                    or (dialog is not None and dialog.worker is not None and not dialog.start_button.isEnabled())
                    or (c.screening_widget is not None and c.screening_widget._busy))

    def delete_workspace(self, root):
        try:
            info = self.store.validate_deletion(root)
            root = Path(info['root'])
            stat = root.stat()
            identity = (stat.st_dev, stat.st_ino, info['ownership']['id'])
        except (OSError, ValueError) as exc:
            self.home.refresh(); self._error(exc); return False
        if self._has_pending_tasks():
            self._error('请先结束后台任务，再删除项目。'); return False
        c = self.controller
        current = self.current_root is not None and self.current_root.is_relative_to(root)
        if current:
            if c.screening_widget and not c.screening_widget.confirm_leave(lambda: self.delete_workspace(root)):
                return False
            if not c._can_replace_annotation() or not self.save_current(): return False
        answer = QtWidgets.QMessageBox.question(self.window, '删除项目',
                    '将“' + info['name'] + '”项目文件夹移入回收站？\n' + str(root),
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if answer != QtWidgets.QMessageBox.Yes: return False
        try:
            # Modal dialogs run an event loop: the path may have changed while waiting.
            latest = self.store.validate_deletion(root)
            stat = root.stat()
            if identity != (stat.st_dev, stat.st_ino, latest['ownership']['id']):
                raise ValueError('项目文件夹已发生变化，请重新选择；未删除任何文件。')
            if self._has_pending_tasks():
                raise ValueError('请先结束后台任务，再删除项目。')
            moved, _ = QtCore.QFile.moveToTrash(str(root))
            if not moved: raise OSError('无法移入系统回收站，项目已保留。')
            if current: self._release_current()
            self.store.forget(root, descendants=True)
        except (OSError, ValueError) as exc:
            self.home.refresh(); self._error(exc); return False
        self.home.refresh()
        return True

    def remove_workspace(self, root):
        """Forget a card without moving or deleting project files."""
        root = Path(root).expanduser().resolve()
        current = root == self.current_root
        c = self.controller
        if current:
            if self._has_pending_tasks():
                self._error('请先结束后台任务，再移除当前项目。'); return False
            if c.screening_widget and not c.screening_widget.confirm_leave(lambda: self.remove_workspace(root)):
                return False
            if not c._can_replace_annotation() or not self.save_current(): return False
        try: self.store.forget(root)
        except (OSError, ValueError) as exc:
            self._error(exc); return False
        if current: self._release_current()
        self.home.refresh()
        return True

    def _release_current(self):
        self._reset_workbench()
        self.current_root = None; self._resume_page = None; self._restore_annotation = False
        self.storage_root = None
        self._current_identity = None
        self.window.config_file = self._default_config_file
        self.window.reload_cfg()
        self.show_home()

    def _resume(self):
        c = self.controller
        if self._resume_page is c.annotation_view: c.show_annotation()
        elif self._resume_page is c.widget and c.widget is not None: c.show_development()
        else: c.show_screening()
        name = self.store.read(self.current_root)['name']
        self.window.setWindowTitle(name + ' · YOLO-BACKPROP')

    def _reset_workbench(self):
        c = self.controller; w = self.window
        c.show_annotation()  # Restore annotation actions before retiring the old pages.
        for name in ('widget', 'screening_widget'):
            page = getattr(c, name)
            if page is not None:
                c.stack.removeWidget(page); page.setParent(None); page.deleteLater(); setattr(c, name, None)
        c._shortcuts = {}; c._visible = {}; c._viewport = None
        w.saved = True
        w.image_root = w.label_root = None
        w.files_list = []; w.current_index = 0
        encoder = getattr(w, 'seganythread', None)
        if encoder is not None:
            encoder.results_dict.clear(); encoder.index = None
        if w.use_segment_anything_video and getattr(w, 'segany_video', None):
            w.segany_video.inference_state = {}
        w.files_dock_widget.update_widget(); w.show_image(0)

    def configure_screening(self, page):
        if self.current_root is None: return
        page.workspace_home = self.show_home
        page.session_loaded.connect(self._screening_loaded)

    def _screening_loaded(self, session):
        if (self.current_root is None or not self._same_current_directory()
                or not self.store.has_metadata(self.current_root) or session.project_root is None
                or session.project_root.parent != self.storage_root / 'projects'):
            return
        try:
            info = self.store.read(self.current_root)
            if not info.get('cover') and session.items:
                self.store.set_cover(self.current_root, session.items[0].source)
            state = info['state']; state['project_name'] = session.project_root.name
            self.store.update(self.current_root, state=state)
            restore, self._restore_annotation = self._restore_annotation, False
            if restore and session.items:
                result = {'image_root': str(session.project_root / 'images'),
                          'label_root': str(session.project_root / 'json'),
                          'files': [item.name for item in session.items]}
                if self.controller.open_screened_project(result):
                    index = state.get('annotation_index', 0)
                    if type(index) is int and 0 <= index < len(session.items): self.window.show_image(index)
        except (OSError, ValueError, TypeError) as exc:
            self._error(exc)

    def configure_development(self, widget):
        if self.current_root is None: return
        root = self.storage_root
        info = self.store.read(self.current_root)
        state = info['state']
        train = widget.train_tab
        config = state.get('training')
        values = train._get_current_config_dict()
        values.update(results_dir=str(root / 'results'), log_dir=str(root / 'logs'))
        if info.get('dataset_yaml'): values['data_yaml'] = info.get('organized_dataset_yaml') or info['dataset_yaml']
        if isinstance(config, dict):
            for key, value in config.items():
                if key not in values: continue
                expected = type(values[key])
                if type(value) is expected or (expected is float and type(value) is int):
                    values[key] = value
        if info.get('organized_dataset_yaml') and values['data_yaml'] == info.get('dataset_yaml'):
            values['data_yaml'] = info['organized_dataset_yaml']
        # Restoring a selection must not initiate a model download.
        blocker = QtCore.QSignalBlocker(train.tr_model._combo)
        train._apply_config_dict(values)
        del blocker
        widget.infer_tab._infer_defaults_done = True
        widget.infer_tab.ir_save.setCurrentText(str(root / 'predict'))
        widget.export_tab.export_output.setCurrentText(str(root / 'exports'))
        widget.logs_tab.lv_log_dir.setCurrentText(train.tr_logs.currentText())
        train.training_started.connect(self.record_training)

    def record_training(self, config):
        if self.current_root is None or not self._same_current_directory() or not self.store.has_metadata(self.current_root): return
        try:
            self.save_current()
            self.store.update(self.current_root, last_training=asdict(config))
            image = training_image(config.data_yaml)
            if image: self.store.set_cover(self.current_root, image, trained=True)
            if self.controller.stack.currentWidget() is self.home: self.home.refresh()
        except (OSError, ValueError, TypeError) as exc:
            self._error('训练已启动，首页记录未更新：' + str(exc))

    def dataset_destination(self):
        if self.current_root is None: return None
        return self.storage_root / 'datasets' / datetime.now().strftime('dataset-%Y%m%d-%H%M%S')
