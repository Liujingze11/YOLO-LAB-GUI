"""Native, responsive workspace cards shown before entering the workbench."""
from pathlib import Path
from datetime import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

from .store import validate_project_name


class CreateProjectDialog(QtWidgets.QDialog):
    def __init__(self, location, parent=None):
        super().__init__(parent)
        self.setWindowTitle('新建项目'); self.resize(600, 300)
        self.location = Path(location)
        layout = QtWidgets.QVBoxLayout(self); layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)
        layout.addWidget(QtWidgets.QLabel('项目名称'))
        self.name_edit = QtWidgets.QLineEdit(self._default_name())
        self.name_edit.setPlaceholderText('留空使用默认名称')
        self.name_edit.setMaxLength(80); layout.addWidget(self.name_edit)
        layout.addWidget(QtWidgets.QLabel('保存位置'))
        location_row = QtWidgets.QHBoxLayout()
        self.location_edit = QtWidgets.QLineEdit(str(self.location))
        self.location_edit.setAccessibleName('项目保存位置')
        self.browse_button = QtWidgets.QPushButton('浏览…')
        self.browse_button.setAutoDefault(False)
        self.browse_button.clicked.connect(self._browse)
        location_row.addWidget(self.location_edit, 1); location_row.addWidget(self.browse_button)
        layout.addLayout(location_row)
        self.destination = QtWidgets.QLabel(); self.destination.setWordWrap(True)
        self.destination.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.destination.setStyleSheet('color: #6e6e73;'); layout.addWidget(self.destination)
        layout.addStretch()
        buttons = QtWidgets.QDialogButtonBox()
        self.create_button = buttons.addButton('创建并打开', buttons.AcceptRole)
        self.create_button.setProperty('glassRole', 'primary')
        buttons.addButton('取消', buttons.RejectRole)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        # Register the default after the button box belongs to this dialog.
        self.create_button.setDefault(True)
        self.name_edit.textChanged.connect(self._update_destination)
        self.location_edit.textChanged.connect(self._update_destination); self._update_destination()
        self.name_edit.setFocus(); self.name_edit.selectAll()

    def _default_name(self):
        name, number = '新项目', 1
        while (self.location / name).exists() or (self.location / name).is_symlink():
            number += 1
            name = '新项目 ' + str(number)
        return name

    def _browse(self):
        location = QtWidgets.QFileDialog.getExistingDirectory(self, '选择项目保存的位置', self.location_edit.text())
        if location: self.location_edit.setText(location)

    def _update_destination(self):
        location = self.location_edit.text().strip()
        self.location = Path(location).expanduser()
        entered_name = self.name_edit.text()
        name = entered_name if entered_name.strip() else self._default_name()
        self._resolved_name = name
        try:
            if not location or not self.location.is_absolute() or not self.location.is_dir():
                self.destination.setText('请选择存在的保存位置')
                self.create_button.setEnabled(False)
                return
            validate_project_name(name)
            destination = self.location / name
            valid = not destination.exists() and not destination.is_symlink()
            hint = '保存到：' + str(destination) if valid else '同名文件夹已存在，请换一个名称'
        except ValueError:
            valid = False
            hint = '项目名称不能包含路径或特殊字符'
        self.destination.setText(hint)
        self.create_button.setEnabled(valid)

    def accept(self):
        self._update_destination()
        if self.create_button.isEnabled():
            self.name_edit.setText(self._resolved_name)
            super().accept()


class WorkspaceCard(QtWidgets.QAbstractButton):
    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.info = info
        self.setText(info['name'])
        self.path_text = info['root']
        home = str(Path.home())
        if self.path_text.startswith(home + '/'):
            self.path_text = '~' + self.path_text[len(home):]
        opened = info.get('last_opened', 0)
        try:
            opened_text = '尚未打开' if opened == 0 else datetime.fromtimestamp(opened).strftime('%m-%d %H:%M')
        except (OSError, OverflowError, TypeError, ValueError): opened_text = '时间未知'
        self.time_text = '最近打开 · ' + opened_text
        self.type_text = {'images': '图片项目', 'isat': '图像标注', 'yolo': 'YOLO 数据集'}.get(info.get('source_kind'), '本地项目')
        if type(info.get('image_count')) is int: self.type_text += ' · ' + str(info['image_count']) + ' 张'
        self.setFixedSize(280, 238)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setMouseTracking(True)
        self.cover = QtGui.QPixmap(info['cover']) if info.get('cover') else QtGui.QPixmap()
        self.setAccessibleName(info['name'])
        self.setAccessibleDescription(info['root'] + ' · ' + self.type_text + ' · ' + self.time_text)
        details = [info['root'], self.type_text]
        if type(info.get('annotation_count')) is int: details.append('已有标注：' + str(info['annotation_count']) + ' 张')
        if info.get('skipped_count'): details.append('跳过损坏图片：' + str(info['skipped_count']) + ' 张')
        if info.get('external'): details.append('工作副本：' + info['storage_root'])
        self.setToolTip('\n'.join(details))
        if not info['available']: self.setEnabled(False)

    def sizeHint(self):
        return QtCore.QSize(280, 238)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1)
        active = self.isEnabled() and (self.underMouse() or self.hasFocus())
        painter.setPen(QtGui.QPen(QtGui.QColor('#77b2fa') if active else QtGui.QColor(255, 255, 255, 240), 2 if active else 1))
        material = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
        material.setColorAt(0, QtGui.QColor(255, 255, 255, 225))
        material.setColorAt(1, QtGui.QColor(250, 250, 250, 155))
        painter.setBrush(material); painter.drawRoundedRect(rect, 18, 18)
        preview = QtCore.QRectF(12, 12, self.width() - 24, 126)
        path = QtGui.QPainterPath(); path.addRoundedRect(preview, 9, 9)
        painter.save(); painter.setClipPath(path)
        painter.fillRect(preview, QtGui.QColor('#f1f1f3'))
        if not self.cover.isNull():
            scaled = self.cover.scaled(int(preview.width()), int(preview.height()),
                                      QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation)
            painter.drawPixmap(int(preview.x() + (preview.width() - scaled.width()) / 2),
                               int(preview.y() + (preview.height() - scaled.height()) / 2), scaled)
        else:
            icon = self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon)
            icon.paint(painter, QtCore.QRect(int(preview.center().x()) - 24, int(preview.center().y()) - 18, 48, 48))
        painter.restore()
        font = QtGui.QFont(self.font()); font.setPointSize(11); font.setBold(True)
        painter.setFont(font); painter.setPen(QtGui.QColor('#1d1d1f'))
        painter.drawText(QtCore.QRect(18, 148, self.width() - 36, 25), QtCore.Qt.AlignVCenter,
                         painter.fontMetrics().elidedText(self.text(), QtCore.Qt.ElideRight, self.width() - 36))
        font.setPointSize(9); font.setBold(False); painter.setFont(font)
        painter.setPen(QtGui.QColor('#6e6e73'))
        painter.drawText(QtCore.QRect(18, 178, self.width() - 36, 20), QtCore.Qt.AlignVCenter,
                         painter.fontMetrics().elidedText(self.path_text, QtCore.Qt.ElideMiddle, self.width() - 36))
        painter.drawText(QtCore.QRect(18, 205, self.width() - 36, 18), QtCore.Qt.AlignVCenter, self.time_text)
        badge = QtCore.QRectF(20, 20, painter.fontMetrics().horizontalAdvance(self.type_text) + 16, 24)
        painter.setPen(QtCore.Qt.NoPen); painter.setBrush(QtGui.QColor(255, 255, 255, 230))
        painter.drawRoundedRect(badge, 6, 6)
        painter.setPen(QtGui.QColor('#48484a')); painter.drawText(badge, QtCore.Qt.AlignCenter, self.type_text)


class WorkspaceHome(QtWidgets.QWidget):
    workspace_requested = QtCore.pyqtSignal(str)
    location_ready = QtCore.pyqtSignal(dict)
    delete_requested = QtCore.pyqtSignal(str)
    remove_requested = QtCore.pyqtSignal(str)

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.cards = []
        self.setObjectName('WorkspaceHome')
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setFont(QtGui.QFont('Noto Sans CJK SC', 10))
        self.setStyleSheet('''
            QWidget#WorkspaceHome, QWidget#WorkspaceCards { background: transparent; }
            QLabel { background: transparent; color: #1d1d1f; }
            QScrollArea { background: transparent; border: none; }
        ''')
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(36, 26, 36, 22); layout.setSpacing(0)
        top = QtWidgets.QHBoxLayout(); top.setSpacing(12)
        logo = QtWidgets.QLabel()
        logo.setPixmap(QtGui.QPixmap(str(Path(__file__).parents[1] / 'yolo-backprop-transparent.svg')).scaled(
            42, 42, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        top.addWidget(logo)
        brand = QtWidgets.QLabel('YOLO-BACKPROP')
        brand.setFont(QtGui.QFont(self.font().family(), 14, QtGui.QFont.Bold)); top.addWidget(brand)
        top.addStretch()
        layout.addLayout(top)
        layout.addSpacing(42)
        heading = QtWidgets.QHBoxLayout(); heading.setSpacing(12)
        title = QtWidgets.QLabel('项目'); title.setFont(QtGui.QFont(self.font().family(), 26, QtGui.QFont.Bold))
        heading.addWidget(title); heading.addStretch()
        self.open_button = QtWidgets.QPushButton('打开项目')
        self.open_button.setToolTip('自动识别项目、图片、图像标注或 YOLO 数据集')
        self.open_button.clicked.connect(self.select_workspace)
        self.create_button = QtWidgets.QPushButton('新建项目')
        self.create_button.setProperty('glassRole', 'primary')
        self.create_button.clicked.connect(self.create_workspace)
        for button in (self.open_button, self.create_button):
            button.setFont(self.font())
            button.setFixedSize(112, 40)
        heading.addWidget(self.open_button); heading.addWidget(self.create_button)
        layout.addLayout(heading); layout.addSpacing(24)
        self.empty_label = QtWidgets.QLabel('还没有项目\n新建项目，或打开图片、标注及数据集文件夹。')
        self.empty_label.setAlignment(QtCore.Qt.AlignCenter)
        self.empty_label.setMinimumHeight(200)
        layout.addWidget(self.empty_label)
        self.scroll = QtWidgets.QScrollArea(); self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.content = QtWidgets.QWidget(); self.content.setObjectName('WorkspaceCards')
        content_layout = QtWidgets.QVBoxLayout(self.content); content_layout.setContentsMargins(0, 0, 0, 0)
        self.grid = QtWidgets.QGridLayout(); self.grid.setContentsMargins(0, 0, 0, 0); self.grid.setSpacing(20)
        self.grid.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        content_layout.addLayout(self.grid); content_layout.addStretch()
        self.scroll.setWidget(self.content); self.content.setAutoFillBackground(False)
        layout.addWidget(self.scroll, 1)
        self.refresh()

    def refresh(self):
        for card in self.cards:
            self.grid.removeWidget(card); card.hide(); card.deleteLater()
        self.cards = []
        infos = self.store.recent()
        self.empty_label.setVisible(not infos)
        for info in infos:
            card = WorkspaceCard(info, self.content)
            if info:
                card.clicked.connect(lambda checked=False, root=info['root']: self.workspace_requested.emit(root))
                card.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
                card.customContextMenuRequested.connect(
                    lambda pos, widget=card, root=info['root']: self._show_context_menu(root, widget.mapToGlobal(pos)))
            self.cards.append(card)
        self._arrange()

    def _arrange(self):
        columns = max(1, min(5, (self.scroll.viewport().width() + 20) // 300))
        for card in self.cards: self.grid.removeWidget(card)
        for index, card in enumerate(self.cards): self.grid.addWidget(card, index // columns, index % columns)
        for column in range(5): self.grid.setColumnStretch(column, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def create_context_menu(self, root):
        menu = QtWidgets.QMenu(self)
        callbacks = [('open', '打开项目', lambda: self.workspace_requested.emit(root)),
                     ('open_folder', '打开文件夹', lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(root))),
                     ('copy_path', '复制路径', lambda: QtWidgets.QApplication.clipboard().setText(root)),
                     ('remove', '从列表移除', lambda: self.remove_requested.emit(root)),
                     ('delete', '删除项目…', lambda: self.delete_requested.emit(root))]
        for key, title, callback in callbacks:
            if key == 'remove': menu.addSeparator()
            action = menu.addAction(title); action.setObjectName(key); action.triggered.connect(callback)
            if key == 'delete':
                try: self.store.validate_deletion(root)
                except (OSError, ValueError, RuntimeError):
                    action.setEnabled(False); action.setToolTip('已有目录只支持从列表移除，保留文件')
        return menu

    def _show_context_menu(self, root, position):
        menu = self.create_context_menu(root)
        try: menu.exec_(position)
        finally: menu.deleteLater()

    def create_workspace(self):
        dialog = CreateProjectDialog(self.store.creation_location(), self)
        accepted = dialog.exec_() == dialog.Accepted
        name = dialog.name_edit.text(); location = dialog.location; dialog.deleteLater()
        if not accepted: return
        try: root = self.store.create(location, name)
        except (OSError, ValueError) as exc:
            QtWidgets.QMessageBox.warning(self, '无法创建项目', str(exc)); return
        try: self.store.remember_creation_location(location)
        except OSError: pass  # A preference failure must not block the newly created project.
        self.refresh(); self.workspace_requested.emit(str(root))

    def select_workspace(self):
        location = QtWidgets.QFileDialog.getExistingDirectory(self, '选择图片或项目文件夹', str(Path.home()))
        if not location: return
        from .operations import run_operation, inspect_project
        try:
            info = run_operation(self, '正在自动识别项目…',
                                 lambda check, progress: inspect_project(self.store, location, check))
        except (OSError, ValueError, RuntimeError) as exc:
            QtWidgets.QMessageBox.warning(self, '无法打开项目', str(exc)); return
        if info is None: return
        # The controller registers only after task and unsaved-work guards pass.
        self.location_ready.emit(info)
