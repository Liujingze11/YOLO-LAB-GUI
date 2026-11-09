"""Image folder screening with a native thumbnail grid and large preview."""
from pathlib import Path
import json
from uuid import uuid4

from PyQt5 import QtCore, QtGui, QtWidgets

from .workers import ScanWorker, PreviewWorker, SaveWorker
from .views import (FolderGrid, FolderDropArea, ImagePreview, TrashStrip, ItemDropArea,
                    dropped_folder, dropped_image, dropped_items, accept_copy, ITEMS_MIME)
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
        self._drag_anchor_state = None
        self._drag_anchor_active = None
        self._context_source = None
        self._preview_requested = None
        self._busy = False
        self._cancelled = False
        self._last_project = None
        self._initial_count = 0
        self._rows = {}
        self._trash_rows = {}
        self._rebuilding = False
        self._layout_initialized = False
        self._trash_count = 0
        self._transfer_token = uuid4().hex
        self.open_button = QtWidgets.QPushButton('打开图片文件夹')
        self.cancel_button = QtWidgets.QPushButton('取消任务')
        self.configure_shortcuts = None
        self.cancel_button.setVisible(False)
        self.open_button.clicked.connect(self._choose_folder)
        self.cancel_button.clicked.connect(self.stop_workers)
        self.grid = FolderGrid()
        self.grid.folder_dropped.connect(self.open_folder)
        self.grid.drag_anchor_requested.connect(self._remember_drag_anchor)
        self.grid.image_drag_started.connect(self._begin_image_drag)
        self.grid.image_drag_finished.connect(self._end_image_drag)
        self.grid.preview_returned.connect(self._return_preview)
        self.grid.transfer_items = lambda mime: self._items_for_transfer(mime, 'trash')
        self.grid.items_dropped.connect(self.restore_items)
        self.grid.currentItemChanged.connect(self._select_current)
        self.grid.itemClicked.connect(lambda row: self._select_current(row) if not self.grid.drag_completed else None)
        self.grid.itemSelectionChanged.connect(self._update_actions)
        self.grid.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self._context_menu)
        self.preview = ImagePreview()
        self.comparison_preview = ImagePreview()
        self._active_preview = self.preview
        self.comparison_preview.empty_message = '拖入另一张图片进行对比'
        self.preview_label = QtWidgets.QLabel('选择图片查看大图')
        self.comparison_label = QtWidgets.QLabel('对比图片')
        for view in (self.preview, self.comparison_preview):
            view.resolve_drop = lambda mime, mode, target=view: self._preview_drop_mode(target, mime, mode)
            view.decorate_mime = self._decorate_preview_mime
            view.activated.connect(lambda target=view: self._activate_preview(target))
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
        self.position_label = QtWidgets.QLabel('0 / 0')
        self.position_label.setAlignment(QtCore.Qt.AlignCenter)
        self.position_label.setMinimumWidth(72)
        self.position_label.setAccessibleName('当前预览图片序号')
        self.preview_controls = QtWidgets.QWidget()
        preview_tools = QtWidgets.QHBoxLayout(self.preview_controls)
        preview_tools.setContentsMargins(0, 0, 0, 0)
        preview_tools.setSpacing(8)
        preview_tools.addStretch()
        preview_tools.addWidget(self.previous_button)
        preview_tools.addWidget(self.position_label)
        preview_tools.addWidget(self.following_button)
        preview_tools.addStretch()
        preview_tools.addWidget(self.fit_button)
        right = QtWidgets.QWidget(); right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0); right_layout.setSpacing(8)
        right_layout.addWidget(preview_columns, 1)
        right_layout.addWidget(self.preview_controls)
        self.splitter = QtWidgets.QSplitter()
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(12)
        self.left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0); left_layout.setSpacing(8)
        self.list_header = QtWidgets.QWidget()
        self.list_header.setFixedHeight(48)
        header = QtWidgets.QHBoxLayout(self.list_header)
        header.setContentsMargins(4, 0, 0, 0); header.setSpacing(8)
        self.images_label = QtWidgets.QLabel('图片 (0)')
        header.addWidget(self.images_label); header.addStretch(); header.addWidget(self.open_button)
        left_layout.addWidget(self.list_header)
        left_layout.addWidget(self.grid, 1)
        self.trash_panel = self._create_trash_panel()
        left_layout.addWidget(self.trash_panel)
        self.splitter.addWidget(self.left_panel); self.splitter.addWidget(right)
        self.splitter.setStretchFactor(0, 1); self.splitter.setStretchFactor(1, 1)
        self.status = QtWidgets.QLabel()
        self.status.hide()
        for label in (self.status, self.preview_label, self.comparison_label):
            label.setProperty('glassRole', 'muted')
        self.status.setWordWrap(True)
        self.progress = QtWidgets.QProgressBar(); self.progress.hide()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(10)
        self.content_stack = QtWidgets.QStackedWidget()
        self.empty_page = self._create_empty_page()
        self.content_stack.addWidget(self.empty_page)
        self.content_stack.addWidget(self.splitter)
        self.task_bar = QtWidgets.QWidget()
        task_layout = QtWidgets.QHBoxLayout(self.task_bar)
        task_layout.setContentsMargins(0, 0, 0, 0)
        task_layout.addWidget(self.status, 1); task_layout.addWidget(self.cancel_button)
        layout.addWidget(self.content_stack, 1)
        layout.addWidget(self.progress); layout.addWidget(self.task_bar)
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

    def _create_empty_page(self):
        page = FolderDropArea()
        page.setObjectName('ScreeningEmptyState')
        page.folder_dropped.connect(self.open_folder)
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        card = QtWidgets.QFrame()
        card.setObjectName('ScreeningImportCard')
        card.setMinimumSize(400, 300)
        card.setMaximumWidth(520)
        card.setAttribute(QtCore.Qt.WA_StyledBackground)
        content = QtWidgets.QVBoxLayout(card)
        content.setContentsMargins(40, 28, 40, 28); content.setSpacing(16)
        icon = QtWidgets.QLabel()
        icon.setPixmap(self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon).pixmap(56, 56))
        icon.setAlignment(QtCore.Qt.AlignCenter)
        self.empty_open_button = QtWidgets.QPushButton('打开图片文件夹')
        self.empty_open_button.setObjectName('ScreeningImportButton')
        self.empty_open_button.setProperty('glassRole', 'primary')
        self.empty_open_button.setFixedSize(184, 42)
        self.empty_open_button.clicked.connect(self._choose_folder)
        hint = QtWidgets.QLabel('或拖入文件夹')
        hint.setProperty('glassRole', 'muted')
        hint.setAlignment(QtCore.Qt.AlignCenter)
        content.addStretch(); content.addWidget(icon)
        content.addWidget(self.empty_open_button, 0, QtCore.Qt.AlignHCenter)
        content.addWidget(hint); content.addStretch()
        layout.addStretch(); layout.addWidget(card, 0, QtCore.Qt.AlignHCenter); layout.addStretch()
        return page

    def _create_trash_panel(self):
        panel = ItemDropArea(); panel.setObjectName('ScreeningTrashPanel')
        panel.transfer_items = lambda mime: self._items_for_transfer(mime, 'images')
        panel.items_dropped.connect(self._remove_items)
        panel.drag_entered.connect(lambda: self.trash_toggle.setChecked(True))
        panel.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        panel.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8); layout.setSpacing(4)
        header = QtWidgets.QHBoxLayout()
        self.trash_label = QtWidgets.QLabel('回收站 (0)')
        self.trash_toggle = QtWidgets.QToolButton()
        self.trash_toggle.setCheckable(True)
        self.trash_toggle.setFixedSize(24, 24)
        self.trash_toggle.toggled.connect(self._toggle_trash)
        header.addWidget(self.trash_toggle); header.addWidget(self.trash_label); header.addStretch()
        self.trash_list = TrashStrip()
        self.trash_list.transfer_items = panel.transfer_items
        self.trash_list.items_dropped.connect(self._remove_items)
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

    def _toggle_trash(self, expanded):
        self.trash_list.setVisible(expanded)
        self.trash_restore_button.setVisible(expanded)
        self.trash_toggle.setArrowType(QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow)
        self.trash_toggle.setAccessibleName('收起回收站' if expanded else '展开回收站')
        self.trash_toggle.setToolTip(self.trash_toggle.accessibleName())

    def _sync_layout_state(self):
        loaded = self.session is not None
        self.content_stack.setCurrentWidget(self.splitter if loaded else self.empty_page)
        if loaded and not self._layout_initialized:
            width = self.content_stack.width()
            self.splitter.setSizes([int(width * .3), int(width * .7)])
            self._layout_initialized = True
        self.empty_page.setEnabled(not self._busy)
        self.task_bar.setVisible(self._busy or bool(self.status.text()))
        self.images_label.setText(f'图片 ({self.grid.count()})')
        trash_count = len(self.session.trash) if loaded else 0
        self.trash_label.setText(f'回收站 ({trash_count})')
        if not trash_count:
            self.trash_toggle.setChecked(False)
        elif trash_count > self._trash_count:
            self.trash_toggle.setChecked(True)
        self._trash_count = trash_count
        self.trash_toggle.setEnabled(bool(trash_count))
        self._toggle_trash(self.trash_toggle.isChecked())
        self.grid.empty_message = ('没有保留的图片\n可从下方回收站恢复' if trash_count else
                                   '文件夹中没有可筛选的图片\n可重新打开图片文件夹')
        self.preview.empty_message = ('从左侧选择图片查看大图' if self.grid.count() else
                                      '没有可预览的图片')
        self.grid.viewport().update(); self.preview.viewport().update()
        self._update_position()

    def _update_position(self):
        total = self.grid.count()
        path = self._active_path()
        row = self._rows.get(path)
        if row is not None:
            text = f'{self.grid.row(row) + 1} / {total}'
        elif path:
            text = '外部图片'
        else:
            text = f'— / {total}' if total else '0 / 0'
        self.position_label.setText(text)

    def _active_path(self):
        return self._comparison_requested if self._active_preview is self.comparison_preview else self._preview_requested

    def _activate_preview(self, view):
        if view is self.comparison_preview and not self._comparison_open: view = self.preview
        self._active_preview = view
        for candidate in (self.preview, self.comparison_preview):
            active = self._comparison_open and candidate is view
            if candidate.property('activePreview') != active:
                candidate.setProperty('activePreview', active)
                candidate.style().unpolish(candidate); candidate.style().polish(candidate); candidate.update()
        if hasattr(self, 'command_actions'): self._update_actions()

    def _items_for_transfer(self, mime, source):
        if self._busy or self.session is None or not self.isEnabled(): return []
        data = dropped_items(mime)
        if not data or data['session'] != self._transfer_token or data['source'] != source: return []
        ids = data['ids']
        if len(set(ids)) != len(ids): return []
        records = self.session.items if source == 'images' else self.session.trash
        available = {item.record_id: item for item in records}
        if any(record_id not in available for record_id in ids): return []
        return [available[record_id] for record_id in ids]

    def _decorate_preview_mime(self, mime, path):
        row = self._rows.get(path)
        if row is not None:
            mime.setData(ITEMS_MIME, json.dumps({'session': self._transfer_token, 'source': 'images',
                         'ids': [row.data(QtCore.Qt.UserRole).record_id]}).encode('utf-8'))

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
        requested = set(items)
        items = [item for item in self.session.trash if item in requested]
        if not items: return
        self.session.restore(items)
        self.grid.blockSignals(True); self.trash_list.blockSignals(True)
        self.grid.clearSelection()
        for asset in items:
            path = str(asset.source)
            row = self._trash_rows.pop(path)
            moved = self.trash_list.takeItem(self.trash_list.row(row))
            moved.setToolTip(path + f'\n{asset.width} × {asset.height}')
            self.grid.addItem(moved); self._rows[path] = moved; moved.setSelected(True)
        self.grid.blockSignals(False); self.trash_list.blockSignals(False)
        if not self._preview_requested:
            self.grid.setCurrentItem(self._rows[str(items[0].source)], QtCore.QItemSelectionModel.NoUpdate)
            self._show_primary(str(items[0].source))
        self.grid.scrollToItem(self._rows[str(items[0].source)])
        self._last_project = None
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
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(8)
        label.setWordWrap(True)
        label.setFixedHeight(48)
        label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        layout.addWidget(label); layout.addWidget(view, 1)
        return panel

    def _apply_shortcuts(self, bindings):
        buttons = {'previous': self.previous_button, 'next': self.following_button,
                   'fit': self.fit_button}
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
        if self.configure_shortcuts is not None:
            self.configure_shortcuts()
            return
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
        self._transfer_token = uuid4().hex
        self.grid.session_token = self.trash_list.session_token = self._transfer_token
        self._initial_count = len(session.items) + len(session.trash)
        self._last_project = None
        self._preview_requested = None
        self.exit_comparison()
        self._rebuild_grid()
        self.open_button.setToolTip('图片来源：' + str(session.origin_root))
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
        if self.grid.pointer_selecting: return
        if not self._rebuilding and not self._busy and self.isVisible() and self.isEnabled(): self._cancelled = False
        asset = row.data(QtCore.Qt.UserRole) if row else None
        self._activate_preview(self.preview)
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
        target = self.comparison_preview if view is self.comparison_preview or mode.endswith('compare') else self.preview
        current = self._comparison_requested if target is self.comparison_preview else self._preview_requested
        other = self._preview_requested if target is self.comparison_preview else self._comparison_requested
        if mode == 'keep' or path == current:
            self._activate_preview(target); return
        if self._comparison_open and current and path == other:
            self._swap_previews(target); return
        if path in self._trash_rows:
            self.restore_items([self._trash_rows[path].data(QtCore.Qt.UserRole)])
        if target is self.comparison_preview:
            self.compare_with(path)
            self._activate_preview(self.comparison_preview)
        else:
            if mode in ('compare_left', 'restore_compare_left'):
                self.compare_with(path, on_left=True)
            else:
                self._show_primary(path)
            self._activate_preview(self.preview)
        target.setFocus(QtCore.Qt.MouseFocusReason)
        self._update_actions()

    def _preview_drop_mode(self, view, mime, mode):
        if self._busy or not self.isEnabled(): return None
        if mime.hasFormat(ITEMS_MIME):
            data = dropped_items(mime)
            if not data or len(self._items_for_transfer(mime, data['source'])) != 1: return None
        path = dropped_image(mime)
        target_right = view is self.comparison_preview or mode == 'compare'
        current = self._comparison_requested if target_right else self._preview_requested
        other = self._preview_requested if target_right else self._comparison_requested
        if path == current: return 'keep'
        if path == other:
            return 'swap' if self._comparison_open and current else 'keep'
        if path in self._trash_rows:
            return 'restore_' + mode if mode in ('compare', 'compare_left') else 'restore'
        return mode

    def _swap_previews(self, target):
        left, right = self.preview.view_state(), self.comparison_preview.view_state()
        self._preview_requested, self._comparison_requested = self._comparison_requested, self._preview_requested
        self._comparison_revision += 1
        if self._comparison_worker: self._comparison_worker.stop()
        for view, state, path in ((self.preview, right, self._preview_requested),
                                  (self.comparison_preview, left, self._comparison_requested)):
            view.restore_view_state(state if state and state[0] == path else None)
        self._start_preview(); self._start_comparison_preview()
        self._refresh_preview_labels()
        self._activate_preview(target)
        target.setFocus(QtCore.Qt.MouseFocusReason)

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
        self._update_position()

    def _remember_drag_anchor(self):
        self._drag_anchor = self._preview_requested or self.preview.displayed_path
        self._drag_anchor_state = self.preview.view_state()
        self._drag_anchor_active = self._active_preview

    def _begin_image_drag(self):
        if self._drag_anchor and self._preview_requested != self._drag_anchor:
            self._preview_requested = self._drag_anchor
            state = self._drag_anchor_state
            self.preview.restore_view_state(state if state and state[0] == self._drag_anchor else None)
            self._start_preview(); self._refresh_preview_labels()

    def _end_image_drag(self, accepted):
        if not accepted and self._drag_anchor_active is not None:
            self._activate_preview(self._drag_anchor_active)
        self._drag_anchor = None
        self._drag_anchor_state = self._drag_anchor_active = None
        self._update_actions()

    def _start_preview(self):
        if self._cancelled or not self._preview_requested or self._preview_worker is not None: return
        if self.preview.displayed_path == self._preview_requested: return
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
        self.comparison_panel.show()
        self._activate_preview(self._active_preview)
        self.comparison_label.setText('拖入图片加入对比')
        self._update_actions()

    def compare_with(self, path, on_left=False):
        path = str(Path(path).expanduser().resolve())
        if not self._preview_requested or not Path(path).is_file(): return False
        if path == self._preview_requested:
            self.status.setText('请选择另一张图片进行对比。'); return False
        original = self.preview.view_state() if on_left else None
        self._comparison_requested = self._preview_requested if on_left else path
        self._comparison_open = True
        self.preview.allow_compare = False
        self._comparison_revision += 1
        if self._comparison_worker: self._comparison_worker.stop()
        self.comparison_panel.show()
        self.comparison_preview.restore_view_state(
            original if original and original[0] == self._comparison_requested else None)
        if on_left: self._show_primary(path)
        self._activate_preview(self._active_preview)
        self._refresh_preview_labels(); self._update_actions()
        self._start_comparison_preview()
        return True

    def _start_comparison_preview(self):
        if self._cancelled or not self._comparison_requested or self._comparison_worker is not None: return
        if self.comparison_preview.displayed_path == self._comparison_requested: return
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
        self.comparison_panel.hide()
        self._activate_preview(self.preview)
        self._update_actions()

    def _navigation_target(self, amount):
        if self._busy or not self.grid.count(): return None
        path = self._active_path()
        row = self._rows.get(path)
        index = self.grid.row(row) if row is not None else (-1 if amount > 0 else self.grid.count())
        other = (self._preview_requested if self._active_preview is self.comparison_preview
                 else self._comparison_requested) if self._comparison_open else None
        index += amount
        while 0 <= index < self.grid.count():
            candidate = str(self.grid.item(index).data(QtCore.Qt.UserRole).source)
            if candidate != other: return candidate
            index += amount
        return None

    def _step(self, amount):
        if self._trash_focused(): return
        path = self._navigation_target(amount)
        if not path: return
        if self._active_preview is self.comparison_preview:
            self.compare_with(path)
        else:
            self.grid.setCurrentItem(self._rows[path])
            self._show_primary(path)
        self._update_actions()

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
        self._remove_items([row.data(QtCore.Qt.UserRole) for row in selected])

    def _remove_items(self, items):
        if self._busy or self.session is None: return
        requested = set(items)
        items = [item for item in self.session.items if item in requested]
        if not items: return
        current = max(0, self.grid.currentRow())
        active = self._active_preview
        self.session.remove(items)
        removed_paths = {str(item.source) for item in items}
        if self._comparison_requested in removed_paths or not self.session.items: self.exit_comparison()
        self.grid.blockSignals(True); self.trash_list.blockSignals(True)
        for item in items:
            path = str(item.source)
            row = self._rows.pop(path)
            moved = self.grid.takeItem(self.grid.row(row)); moved.setSelected(False)
            moved.setToolTip(moved.text() + '\n双击恢复')
            self.trash_list.addItem(moved); self._trash_rows[path] = moved
        self.grid.blockSignals(False); self.trash_list.blockSignals(False)
        self.trash_list.scrollToItem(self.trash_list.item(self.trash_list.count() - 1))
        self._last_project = None
        if not self.grid.count():
            self._show_primary(None)
        elif self._preview_requested in removed_paths:
            candidates = [self.grid.item(i) for i in range(self.grid.count())]
            candidates = candidates[current:] + candidates[:current]
            replacement = next((row for row in candidates
                                if str(row.data(QtCore.Qt.UserRole).source) != self._comparison_requested), None)
            if replacement is None:
                self.exit_comparison(); replacement = candidates[0]
            self.grid.setCurrentItem(replacement)
            self._show_primary(str(replacement.data(QtCore.Qt.UserRole).source))
        self._activate_preview(active)
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
        if busy:
            self.progress.setRange(0, 0)
            self.status.show()
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
            if getattr(self, 'source_description', ''): message = self.source_description + ' · ' + message
            if is_dirty(self.session): message += '（有未保存的筛选修改）'
            if self._last_project: message += '\n项目：' + self._last_project['project_root']
            self.status.setText(message)

    def _error(self, message):
        if not self._cancelled:
            self.status.setText(message); self.status.show(); self.task_bar.show()
            QtWidgets.QMessageBox.warning(self, '数据筛选', message)

    def _update_actions(self):
        count = len(self.grid.selectedItems()) if hasattr(self, 'grid') else 0
        self.trash_list.setEnabled(not self._busy)
        self.restore_trash_action.setEnabled(not self._busy and bool(self.trash_list.selectedItems()))
        self._sync_layout_state()
        if not hasattr(self, 'command_actions'): return
        has_items = bool(self.session and self.session.items)
        previous = self._navigation_target(-1) is not None
        following = self._navigation_target(1) is not None
        enabled = {'rename': not self._busy and count == 1, 'remove': not self._busy and count > 0,
                   'save': not self._busy and self.session is not None,
                   'trash': not self._busy and bool(self.session and self.session.trash),
                   'copy_path': count > 0, 'open_folder': count > 0, 'previous': previous, 'next': following,
                   'fit': bool(self.preview.displayed_path), 'compare': bool(self._preview_requested) and not self._busy,
                   'exit_compare': self._comparison_open, 'select_all': has_items}
        for key, value in enabled.items(): self.command_actions[key].setEnabled(value)
        self.previous_button.setEnabled(previous); self.following_button.setEnabled(following)
        self.fit_button.setEnabled(enabled['fit'])
        self.settings_action.setEnabled(not self._busy)

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
