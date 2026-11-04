"""Image folder screening with a native thumbnail grid and large preview."""
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets
from ISAT.workbench import ElidedLabel

from .workers import ScanWorker, PreviewWorker, SaveWorker
from .views import FolderGrid, ImagePreview, TrashStrip, dropped_folder, accept_copy
from .shortcuts import COMMANDS, ShortcutSettings, ShortcutDialog
from .workspace import Workspace, WorkspaceSettings, is_dirty
from .dialogs import TrashDialog


class DataScreeningWidget(QtWidgets.QWidget):
    project_ready = QtCore.pyqtSignal(dict)
    project_saved = QtCore.pyqtSignal(dict)
    session_loaded = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('DataScreening')
        if parent is not None: self.setFont(parent.font())
        self.setAcceptDrops(True)
        self.session = None
        self.before_import = lambda: True
        self.before_save = lambda: True
        self.category_provider = lambda: []
        self.workspace_settings = WorkspaceSettings()
        self.workspace = None
        self.workspace_home = None
        if self.workspace_settings.root and self.workspace_settings.root.is_dir():
            try: self.workspace = Workspace(self.workspace_settings.root)
            except (OSError, ValueError): pass
        self._after_save_callback = None
        self._save_import = False
        self._saved_preview_ids = (None, None)
        self._scan_worker = self._export_worker = self._preview_worker = None
        self._comparison_worker = None
        self._comparison_requested = None
        self._comparison_revision = 0
        self._comparison_open = False
        self._drag_anchor = None
        self._context_source = None
        self._preview_requested = None
        self._busy = False
        self._cancelled = False
        self._last_project = None
        self._initial_count = 0
        self._rows = {}
        self._trash_rows = {}
        self._rebuilding = False
        self.open_button = QtWidgets.QPushButton('打开文件夹')
        self.save_button = QtWidgets.QPushButton('保存筛选')
        self.save_button.clicked.connect(lambda: self.save_screening())
        self.import_button = QtWidgets.QPushButton('导入数据标注')
        self.import_button.setProperty('glassRole', 'primary')
        self.cancel_button = QtWidgets.QPushButton('取消任务')
        self.shortcut_button = QtWidgets.QPushButton('快捷键…')
        self.shortcut_button.clicked.connect(self._configure_shortcuts)
        self.cancel_button.setVisible(False)
        self.open_button.clicked.connect(self._choose_folder)
        self.import_button.clicked.connect(self._import)
        self.cancel_button.clicked.connect(self.stop_workers)
        self.source_label = ElidedLabel('选择图片文件夹')
        self.source_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        tools = QtWidgets.QHBoxLayout()
        tools.addWidget(self.open_button)
        tools.addStretch()
        tools.addWidget(self.shortcut_button)
        tools.addWidget(self.cancel_button); tools.addWidget(self.save_button); tools.addWidget(self.import_button)
        self.grid = FolderGrid()
        self.grid.folder_dropped.connect(self.open_folder)
        self.grid.drag_anchor_requested.connect(self._remember_drag_anchor)
        self.grid.image_drag_started.connect(self._begin_image_drag)
        self.grid.image_drag_finished.connect(self._end_image_drag)
        self.grid.preview_returned.connect(self._return_preview)
        self.grid.currentItemChanged.connect(self._select_current)
        self.grid.itemClicked.connect(self._select_current)
        self.grid.itemSelectionChanged.connect(self._update_actions)
        self.grid.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self._context_menu)
        self.preview = ImagePreview()
        self.comparison_preview = ImagePreview()
        self.preview_label = QtWidgets.QLabel('选择图片查看大图')
        self.comparison_label = QtWidgets.QLabel('对比图片')
        for view in (self.preview, self.comparison_preview):
            view.image_dropped.connect(lambda path, mode, target=view: self._drop_preview(target, path, mode))
            view.folder_dropped.connect(self.open_folder)
            view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            view.customContextMenuRequested.connect(lambda position, target=view: self._preview_context_menu(target, position))
        self.primary_panel = self._make_preview_panel(self.preview, self.preview_label)
        self.comparison_panel = self._make_preview_panel(self.comparison_preview, self.comparison_label)
        self.comparison_panel.hide()
        preview_columns = QtWidgets.QWidget()
        columns_layout = QtWidgets.QHBoxLayout(preview_columns)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(8)
        columns_layout.addWidget(self.primary_panel, 1)
        columns_layout.addWidget(self.comparison_panel, 1)
        self.fit_button = QtWidgets.QPushButton('适应窗口')
        self.fit_button.clicked.connect(lambda: self.command_actions['fit'].trigger())
        self.previous_button = QtWidgets.QPushButton('上一张')
        self.previous_button.clicked.connect(lambda: self.command_actions['previous'].trigger())
        self.following_button = QtWidgets.QPushButton('下一张')
        self.following_button.clicked.connect(lambda: self.command_actions['next'].trigger())
        self.exit_compare_button = QtWidgets.QPushButton('退出对比')
        self.exit_compare_button.clicked.connect(lambda: self.command_actions['exit_compare'].trigger())
        self.exit_compare_button.hide()
        preview_tools = QtWidgets.QHBoxLayout()
        preview_tools.addWidget(self.previous_button); preview_tools.addWidget(self.following_button)
        preview_tools.addStretch(); preview_tools.addWidget(self.exit_compare_button); preview_tools.addWidget(self.fit_button)
        right = QtWidgets.QWidget(); right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(preview_columns, 1)
        right_layout.addLayout(preview_tools)
        self.splitter = QtWidgets.QSplitter()
        self.splitter.setChildrenCollapsible(False)
        self.left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0); left_layout.setSpacing(8)
        left_layout.addWidget(self.grid, 1)
        self.trash_panel = self._create_trash_panel()
        left_layout.addWidget(self.trash_panel)
        self.splitter.addWidget(self.left_panel); self.splitter.addWidget(right)
        self.splitter.setSizes([430, 730])
        self.status = QtWidgets.QLabel('删除和重命名仅作用于筛选结果，原图片保持不变。')
        for label in (self.source_label, self.status,
                      self.preview_label, self.comparison_label):
            label.setProperty('glassRole', 'muted')
        self.status.setWordWrap(True)
        self.progress = QtWidgets.QProgressBar(); self.progress.hide()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(10)
        self.command_bar = QtWidgets.QFrame()
        self.command_bar.setProperty('glassRole', 'commandBar')
        command_layout = QtWidgets.QVBoxLayout(self.command_bar)
        command_layout.setContentsMargins(12, 8, 12, 8); command_layout.setSpacing(6)
        command_layout.addWidget(self.source_label)
        command_layout.addLayout(tools)
        layout.addWidget(self.command_bar); layout.addWidget(self.splitter, 1)
        layout.addWidget(self.progress); layout.addWidget(self.status)
        self.shortcut_settings = ShortcutSettings()
        self.command_actions = {}
        callbacks = {'rename': self._rename_selected, 'remove': self._remove_selected,
                     'save': self.save_screening, 'trash': self.show_trash,
                     'copy_path': self._copy_paths, 'open_folder': self._open_source_folder,
                     'previous': lambda: self._step(-1), 'next': lambda: self._step(1),
                     'fit': self.fit_previews, 'compare': self._compare_selected,
                     'exit_compare': self.exit_comparison, 'select_all': self._select_all}
        for key, (label, default) in COMMANDS.items():
            action = QtWidgets.QAction(label, self)
            action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
            action.triggered.connect(callbacks[key])
            self.addAction(action)
            self.command_actions[key] = action
        self.settings_action = QtWidgets.QAction('快捷键设置…', self)
        self.settings_action.triggered.connect(self._configure_shortcuts)
        self._apply_shortcuts(self.shortcut_settings.bindings)
        self._update_actions()

    def _create_trash_panel(self):
        panel = QtWidgets.QWidget(); panel.setObjectName('ScreeningTrashPanel')
        panel.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        panel.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8); layout.setSpacing(4)
        header = QtWidgets.QHBoxLayout()
        self.trash_label = QtWidgets.QLabel('回收站 (0)')
        header.addWidget(self.trash_label); header.addStretch()
        self.trash_list = TrashStrip()
        self.restore_trash_action = QtWidgets.QAction('恢复选中', self)
        self.restore_trash_action.triggered.connect(self._restore_selected_trash)
        self.trash_restore_button = QtWidgets.QToolButton()
        self.trash_restore_button.setDefaultAction(self.restore_trash_action)
        header.addWidget(self.trash_restore_button)
        layout.addLayout(header); layout.addWidget(self.trash_list)
        self.trash_list.itemDoubleClicked.connect(lambda row: self.restore_items([row.data(QtCore.Qt.UserRole)]))
        self.trash_list.itemSelectionChanged.connect(self._update_actions)
        self.trash_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.trash_list.customContextMenuRequested.connect(self._trash_context_menu)
        return panel

    def _trash_focused(self):
        focus = QtWidgets.QApplication.focusWidget()
        return focus is not None and self.trash_panel.isAncestorOf(focus)

    def _select_all(self):
        (self.trash_list if self._trash_focused() else self.grid).selectAll()

    def _restore_selected_trash(self):
        self.restore_items([row.data(QtCore.Qt.UserRole) for row in self.trash_list.selectedItems()])

    def _trash_context_menu(self, position):
        row = self.trash_list.itemAt(position)
        if row is None: return
        if not row.isSelected(): self.trash_list.setCurrentItem(row)
        menu = QtWidgets.QMenu(self)
        menu.addAction(self.restore_trash_action)
        menu.exec_(self.trash_list.viewport().mapToGlobal(position)); menu.deleteLater()

    def choose_workspace(self):
        if self._busy: return False
        if self.workspace_home:
            self.workspace_home(); return False
        root = QtWidgets.QFileDialog.getExistingDirectory(self, '选择工作空间（保存项目副本）',
                                                          str(self.workspace.root) if self.workspace else str(Path.home()))
        if not root: return False
        try: selected = self.workspace_settings.select(root)
        except (OSError, ValueError) as exc:
            self._error(str(exc)); return False
        self.workspace = selected
        return True

    def create_trash_dialog(self):
        return TrashDialog(self.session, self.restore_items, self)

    def show_trash(self):
        if self._busy or not self.session: return
        dialog = self.create_trash_dialog(); dialog.exec_(); dialog.deleteLater()

    def restore_items(self, items):
        if self._busy or self.session is None: return
        items = [item for item in items if item in self.session.trash]
        if not items: return
        self.session.restore(items)
        self._rebuild_grid(primary_id=items[0].record_id); self._last_project = None
        self._summary(); self._update_actions()

    def confirm_leave(self, continuation=None):
        if not is_dirty(self.session): return True
        answer = QtWidgets.QMessageBox.question(self, '未保存的筛选', '是否保存当前筛选修改？',
                QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Save)
        if answer == QtWidgets.QMessageBox.Discard: return True
        if answer == QtWidgets.QMessageBox.Save:
            if self.save_screening(): self._after_save_callback = continuation
        return False

    def _make_preview_panel(self, view, label):
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(4)
        label.setWordWrap(True)
        label.setFixedHeight(label.fontMetrics().height() * 2 + 4)
        layout.addWidget(label); layout.addWidget(view, 1)
        return panel

    def _apply_shortcuts(self, bindings):
        buttons = {'previous': self.previous_button, 'next': self.following_button,
                   'fit': self.fit_button, 'exit_compare': self.exit_compare_button}
        for key, action in self.command_actions.items():
            action.setShortcut(QtGui.QKeySequence(bindings[key]))
            key_text = action.shortcut().toString(QtGui.QKeySequence.NativeText)
            action.setToolTip(action.text() + (' (' + key_text + ')' if key_text else ''))
            if key in buttons: buttons[key].setToolTip(action.toolTip())

    def update_shortcuts(self, bindings):
        self._apply_shortcuts(self.shortcut_settings.save(bindings))

    def create_shortcut_dialog(self):
        return ShortcutDialog(self.shortcut_settings.bindings, self.update_shortcuts, self)

    def _configure_shortcuts(self):
        dialog = self.create_shortcut_dialog()
        dialog.exec_(); dialog.deleteLater()

    def _copy_paths(self):
        paths = [self._context_source] if self._context_source else [str(row.data(QtCore.Qt.UserRole).source) for row in self.grid.selectedItems()]
        QtWidgets.QApplication.clipboard().setText('\n'.join(paths))

    def _open_source_folder(self):
        row = self.grid.currentItem()
        path = self._context_source or (str(row.data(QtCore.Qt.UserRole).source) if row else None)
        if path: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(Path(path).parent)))

    def fit_previews(self):
        self.preview.fit_image()
        if self._comparison_requested: self.comparison_preview.fit_image()

    def dragEnterEvent(self, event):
        accept_copy(event) if dropped_folder(event.mimeData()) and not self._busy else event.ignore()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        folder = dropped_folder(event.mimeData())
        if folder and not self._busy:
            accept_copy(event)
            if event.isAccepted(): self.open_folder(folder)
        else:
            event.ignore()

    def _choose_folder(self):
        root = QtWidgets.QFileDialog.getExistingDirectory(self, '选择图片文件夹')
        if root: self.open_folder(root)

    def open_folder(self, root, project=False):
        if self._busy: return
        if not self.workspace and not self.choose_workspace(): return
        if not self.confirm_leave(lambda: self.open_folder(root, project)): return
        self._cancelled = False
        self._set_busy(True)
        self.status.setText('正在打开项目…' if project else '正在将图片和已有标注复制到工作空间…')
        worker = ScanWorker(root, self, self.workspace, project)
        self._scan_worker = worker
        worker.loaded.connect(self._loaded)
        worker.thumbnail.connect(self._thumbnail)
        worker.progress.connect(self._progress)
        worker.failed.connect(self._error)
        worker.finished.connect(lambda: self._work_finished(worker))
        worker.start()

    def _loaded(self, session):
        if self._cancelled: return
        self.session = session
        self._initial_count = len(session.items) + len(session.trash)
        self._last_project = None
        self._preview_requested = None
        self.exit_comparison()
        self._rebuild_grid()
        self.source_label.setText(session.origin_root.name)
        self.source_label.setToolTip(str(session.origin_root))
        self.session_loaded.emit(session)

    def _rebuild_grid(self, primary_id=None, comparison_id=None):
        self._rebuilding = True
        icons = {(row.data(QtCore.Qt.UserRole).record_id or str(row.data(QtCore.Qt.UserRole).source)): row.icon()
                 for row in list(self._rows.values()) + list(self._trash_rows.values())}
        self.grid.blockSignals(True)
        self.grid.clear(); self.preview.clear_image(); self._rows.clear()
        self.trash_list.blockSignals(True)
        self.trash_list.clear(); self._trash_rows.clear()
        placeholder = self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon)
        for asset in self.session.items:
            row = QtWidgets.QListWidgetItem(icons.get(asset.record_id or str(asset.source), placeholder), asset.name)
            row.setData(QtCore.Qt.UserRole, asset)
            row.setToolTip(str(asset.source) + f'\n{asset.width} × {asset.height}')
            self.grid.addItem(row)
            self._rows[str(asset.source)] = row
        for asset in self.session.trash:
            row = QtWidgets.QListWidgetItem(icons.get(asset.record_id or str(asset.source), placeholder), asset.name)
            row.setData(QtCore.Qt.UserRole, asset); row.setToolTip(asset.name + '\n双击恢复')
            self.trash_list.addItem(row); self._trash_rows[str(asset.source)] = row
        self.grid.blockSignals(False)
        self.trash_list.blockSignals(False)
        index = next((i for i, item in enumerate(self.session.items) if item.record_id == primary_id), 0)
        if self.session.items: self.grid.setCurrentRow(index)
        else: self._show_primary(None)
        self.exit_comparison()
        compared = next((item for item in self.session.items if item.record_id == comparison_id), None)
        if compared: self.compare_with(str(compared.source))
        self._rebuilding = False

    def _thumbnail(self, path, image):
        row = self._rows.get(path) or self._trash_rows.get(path)
        if row is not None: row.setIcon(QtGui.QIcon(QtGui.QPixmap.fromImage(image)))

    def _select_current(self, row, previous=None):
        if not self._rebuilding and not self._busy and self.isVisible() and self.isEnabled(): self._cancelled = False
        asset = row.data(QtCore.Qt.UserRole) if row else None
        self._show_primary(str(asset.source) if asset else None)
        self._update_actions()

    def _show_primary(self, path):
        self._preview_requested = path
        if path != self.preview.displayed_path:
            self.preview.clear_image()
            self._start_preview()
        self._refresh_preview_labels()
        self.preview.allow_compare = bool(path and not self._comparison_open)

    def _drop_preview(self, view, path, mode):
        if self._busy: return
        if view is self.comparison_preview or mode == 'compare':
            self.compare_with(path)
        else:
            if path == self._comparison_requested: self.exit_comparison()
            self._show_primary(path)
        self._update_actions()

    def _return_preview(self, path):
        if self._busy: return
        if path == self._comparison_requested:
            self.exit_comparison()
        elif path == self._preview_requested:
            remaining = self._comparison_requested
            self.exit_comparison(); self._show_primary(remaining)
        self._update_actions()

    def _refresh_preview_labels(self):
        for path, label, view in ((self._preview_requested, self.preview_label, self.preview),
                                  (self._comparison_requested, self.comparison_label, self.comparison_preview)):
            row = self._rows.get(path)
            asset = row.data(QtCore.Qt.UserRole) if row else None
            name = asset.name if asset else Path(path).name if path else '选择图片查看大图'
            size = f'{asset.width} × {asset.height}' if asset else ''
            if not size and view.displayed_path == path and path:
                size = f'{int(view.sceneRect().width())} × {int(view.sceneRect().height())}'
            label.setText(name + ('   ·   ' + size if size else ''))
            label.setToolTip(path or '')

    def _remember_drag_anchor(self):
        self._drag_anchor = self._preview_requested or self.preview.displayed_path

    def _begin_image_drag(self):
        if self._drag_anchor: self._show_primary(self._drag_anchor)

    def _end_image_drag(self, accepted):
        self._drag_anchor = None
        if not accepted: self._select_current(self.grid.currentItem())

    def _start_preview(self):
        if self._cancelled or not self._preview_requested or self._preview_worker is not None: return
        worker = PreviewWorker(self._preview_requested, self)
        self._preview_worker = worker
        worker.ready.connect(self._preview_ready)
        worker.failed.connect(lambda message: self.status.setText(message) if worker.path == self._preview_requested else None)
        worker.finished.connect(lambda: self._preview_finished(worker))
        worker.start()

    def _preview_ready(self, path, image):
        if path == self._preview_requested:
            self.preview.show_image(path, image)
            self._refresh_preview_labels(); self._update_actions()

    def _preview_finished(self, worker):
        if self._preview_worker is worker: self._preview_worker = None
        if self._preview_requested and self._preview_requested != worker.path: self._start_preview()
        worker.deleteLater()

    def _compare_selected(self):
        if not self._preview_requested or self._busy: return
        self._comparison_open = True
        self.preview.allow_compare = False
        self.comparison_panel.show(); self.exit_compare_button.show()
        self.comparison_label.setText('拖入图片加入对比')
        self._update_actions()

    def compare_with(self, path):
        path = str(Path(path).expanduser().resolve())
        if not self._preview_requested or not Path(path).is_file(): return False
        if path == self._preview_requested:
            self.status.setText('请选择另一张图片进行对比。'); return False
        self._comparison_requested = path
        self._comparison_open = True
        self.preview.allow_compare = False
        self._comparison_revision += 1
        if self._comparison_worker: self._comparison_worker.stop()
        self.comparison_preview.clear_image()
        self.comparison_panel.show(); self.exit_compare_button.show()
        self._refresh_preview_labels(); self._update_actions()
        self._start_comparison_preview()
        return True

    def _start_comparison_preview(self):
        if self._cancelled or not self._comparison_requested or self._comparison_worker is not None: return
        revision = self._comparison_revision
        worker = PreviewWorker(self._comparison_requested, self)
        self._comparison_worker = worker
        worker.ready.connect(lambda path, image: self._comparison_ready(revision, path, image))
        worker.failed.connect(lambda message: self.status.setText(message) if revision == self._comparison_revision else None)
        worker.finished.connect(lambda: self._comparison_finished(worker, revision))
        worker.start()

    def _comparison_ready(self, revision, path, image):
        if revision == self._comparison_revision and path == self._comparison_requested:
            self.comparison_preview.show_image(path, image)
            self._refresh_preview_labels(); self._update_actions()

    def _comparison_finished(self, worker, revision):
        if self._comparison_worker is worker: self._comparison_worker = None
        if revision != self._comparison_revision: self._start_comparison_preview()
        worker.deleteLater()

    def exit_comparison(self):
        self._comparison_requested = None
        self._comparison_open = False
        self.preview.allow_compare = bool(self._preview_requested)
        self._comparison_revision += 1
        if self._comparison_worker: self._comparison_worker.stop()
        self.comparison_preview.clear_image()
        self.comparison_panel.hide(); self.exit_compare_button.hide()
        self._update_actions()

    def _step(self, amount):
        if self._trash_focused(): return
        if self.grid.count():
            self.grid.setCurrentRow(max(0, min(self.grid.count() - 1, self.grid.currentRow() + amount)))

    def _rename_selected(self):
        selected = self.grid.selectedItems()
        if self._busy or self._trash_focused() or len(selected) != 1: return
        row = selected[0]; asset = row.data(QtCore.Qt.UserRole)
        name, ok = QtWidgets.QInputDialog.getText(self, '重命名', '新文件名（不含扩展名）：', text=Path(asset.name).stem)
        if not ok: return
        try:
            self.session.rename(asset, name)
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, '重命名', str(exc)); return
        row.setText(asset.name)
        self._last_project = None
        self._refresh_preview_labels()
        self._summary()

    def _remove_selected(self):
        selected = self.grid.selectedItems()
        if self._busy or self._trash_focused() or not selected: return
        current = self.grid.currentRow()
        self.session.remove([row.data(QtCore.Qt.UserRole) for row in selected])
        removed_paths = {str(row.data(QtCore.Qt.UserRole).source) for row in selected}
        if self._comparison_requested in removed_paths or not self.session.items: self.exit_comparison()
        for row in selected:
            path = str(row.data(QtCore.Qt.UserRole).source)
            self._rows.pop(path, None)
            moved = self.grid.takeItem(self.grid.row(row)); moved.setSelected(False)
            moved.setToolTip(moved.text() + '\n双击恢复')
            self.trash_list.addItem(moved); self._trash_rows[path] = moved
        self.trash_list.scrollToItem(self.trash_list.item(self.trash_list.count() - 1))
        self._last_project = None
        if self.grid.count(): self.grid.setCurrentRow(min(current, self.grid.count() - 1))
        else: self._select_current(None)
        self._summary(); self._update_actions()

    def _context_menu(self, position):
        if not self.grid.selectedItems(): return
        menu = self.create_context_menu()
        menu.exec_(self.grid.viewport().mapToGlobal(position)); menu.deleteLater()

    def create_context_menu(self):
        self._update_actions()
        menu = QtWidgets.QMenu(self)
        for group in [('rename', 'remove', 'select_all'), ('copy_path', 'open_folder'), ('compare', 'exit_compare', 'fit'), ('previous', 'next')]:
            if menu.actions(): menu.addSeparator()
            for key in group: menu.addAction(self.command_actions[key])
        menu.addSeparator(); menu.addAction(self.settings_action)
        return menu

    def _preview_context_menu(self, view, position):
        if not view.displayed_path: return
        self._context_source = view.displayed_path
        menu = QtWidgets.QMenu(self)
        for key in ('copy_path', 'open_folder', 'fit', 'compare', 'exit_compare'):
            menu.addAction(self.command_actions[key])
        menu.addSeparator(); menu.addAction(self.settings_action)
        try: menu.exec_(view.viewport().mapToGlobal(position))
        finally:
            self._context_source = None
            menu.deleteLater()

    def _import(self):
        if self._busy or not self.session or not self.session.items or not self.before_import(): return
        self.save_screening(import_after=True)

    def save_screening(self, import_after=False):
        if self._busy or not self.session or not self.before_save(): return False
        self._save_import = import_after
        ids = []
        for path in (self._preview_requested, self._comparison_requested):
            row = self._rows.get(path)
            ids.append(row.data(QtCore.Qt.UserRole).record_id if row else None)
        self._saved_preview_ids = tuple(ids)
        self._start_save()
        return True

    def _start_save(self, purge=False):
        self._cancelled = False
        self._set_busy(True)
        self.status.setText('正在清理回收站副本…' if purge else '正在保存筛选项目…')
        worker = SaveWorker(self.session, self.category_provider(), self, purge)
        self._export_worker = worker
        worker.failed.connect(self._error)
        worker.progress.connect(self._progress)
        worker.finished.connect(lambda: self._work_finished(worker))
        worker.start()

    def _confirm_purge(self):
        dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, '筛选已保存 · 清理回收站',
                    f'筛选已成功保存。是否永久删除回收站中的 {len(self.session.trash)} 张图片副本及对应 JSON？\n'
                    '原始图片和原始标注不会删除。选择“保留”后仍可从回收站恢复。', parent=self)
        dialog.setDetailedText('\n'.join(item.name for item in self.session.trash))
        purge = dialog.addButton('永久删除副本', dialog.DestructiveRole)
        keep = dialog.addButton('保留在回收站', dialog.RejectRole)
        dialog.setDefaultButton(keep); dialog.setEscapeButton(keep)
        dialog.exec_()
        return dialog.clickedButton() is purge

    def _finish_saved(self, worker):
        if worker.result is None:
            self._after_save_callback = None; self._save_import = False
            return
        self._last_project = worker.result
        self._rebuild_grid(*self._saved_preview_ids)
        self._summary(); self._update_actions()
        if self._cancelled:
            self._after_save_callback = None; self._save_import = False
            return
        if not worker.purge and self.session.trash and self._confirm_purge():
            self._start_save(purge=True); return
        if self._save_import and self.session.items: self.project_ready.emit(self._last_project)
        else: self.project_saved.emit(self._last_project)
        self._save_import = False
        continuation, self._after_save_callback = self._after_save_callback, None
        if continuation: QtCore.QTimer.singleShot(0, continuation)

    def _set_busy(self, busy):
        self._busy = busy
        self.open_button.setEnabled(not busy)
        self.cancel_button.setVisible(busy)
        self.progress.setVisible(busy)
        if busy: self.progress.setRange(0, 0)
        self._update_actions()

    def _progress(self, current, total, name):
        self.progress.setRange(0, max(1, total)); self.progress.setValue(current)

    def _work_finished(self, worker):
        if self._scan_worker is worker: self._scan_worker = None
        if self._export_worker is worker: self._export_worker = None
        worker.deleteLater()
        self._set_busy(False)
        self._summary()
        if self._cancelled and self.session is None: self.status.setText('任务已取消，可以重新拖入图片文件夹。')
        if isinstance(worker, SaveWorker): self._finish_saved(worker)

    def _summary(self):
        if self.session:
            count = len(self.session.items)
            message = f'保留 {count} 张 · 回收站 {len(self.session.trash)} 张 · 跳过损坏图片 {len(self.session.skipped)} 张。仅操作工作空间副本。'
            if is_dirty(self.session): message += '（有未保存的筛选修改）'
            if self._last_project: message += '\n项目：' + self._last_project['project_root']
            self.status.setText(message)

    def _error(self, message):
        if not self._cancelled: QtWidgets.QMessageBox.warning(self, '数据筛选', message)

    def _update_actions(self):
        count = len(self.grid.selectedItems()) if hasattr(self, 'grid') else 0
        self.import_button.setEnabled(not self._busy and bool(self.session and self.session.items))
        self.save_button.setEnabled(not self._busy and self.session is not None)
        self.trash_list.setEnabled(not self._busy)
        self.restore_trash_action.setEnabled(not self._busy and bool(self.trash_list.selectedItems()))
        self.trash_label.setText(f'回收站 ({len(self.session.trash) if self.session else 0})')
        if not hasattr(self, 'command_actions'): return
        has_items = bool(self.session and self.session.items)
        enabled = {'rename': not self._busy and count == 1, 'remove': not self._busy and count > 0,
                   'save': self.save_button.isEnabled(), 'trash': not self._busy and bool(self.session and self.session.trash),
                   'copy_path': count > 0, 'open_folder': count > 0, 'previous': has_items, 'next': has_items,
                   'fit': bool(self.preview.displayed_path), 'compare': bool(self._preview_requested) and not self._busy,
                   'exit_compare': self._comparison_open, 'select_all': has_items}
        for key, value in enabled.items(): self.command_actions[key].setEnabled(value)
        self.previous_button.setEnabled(has_items); self.following_button.setEnabled(has_items)
        self.fit_button.setEnabled(enabled['fit'])
        self.shortcut_button.setEnabled(not self._busy); self.settings_action.setEnabled(not self._busy)

    def active_workers(self):
        return [worker for worker in (self._scan_worker, self._export_worker, self._preview_worker, self._comparison_worker)
                if worker is not None and worker.isRunning()]

    def stop_workers(self):
        self._cancelled = True
        self._preview_requested = None
        self.exit_comparison()
        for worker in self.active_workers(): worker.stop()

    def closeEvent(self, event):
        if not self._busy and not self.confirm_leave(self.close):
            event.ignore(); return
        self.stop_workers()
        if self.active_workers(): event.ignore()
        else: super().closeEvent(event)
