"""Native, responsive workspace cards shown before entering the workbench."""
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from .store import validate_project_name


class CreateProjectDialog(QtWidgets.QDialog):
    def __init__(self, location, parent=None):
        super().__init__(parent)
        self.setWindowTitle('新建项目'); self.resize(560, 220)
        self.location = Path(location)
        layout = QtWidgets.QVBoxLayout(self); layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)
        layout.addWidget(QtWidgets.QLabel('项目名称'))
        self.name_edit = QtWidgets.QLineEdit(self._default_name())
        self.name_edit.setPlaceholderText('留空使用默认名称')
        self.name_edit.setMaxLength(80); layout.addWidget(self.name_edit)
        self.destination = QtWidgets.QLabel(); self.destination.setWordWrap(True)
        self.destination.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.destination.setStyleSheet('color: #6e6e73;'); layout.addWidget(self.destination)
        layout.addStretch()
        buttons = QtWidgets.QDialogButtonBox()
        self.create_button = buttons.addButton('创建', buttons.AcceptRole)
        buttons.addButton('取消', buttons.RejectRole)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        # Register the default after the button box belongs to this dialog.
        self.create_button.setDefault(True)
        self.name_edit.textChanged.connect(self._update_destination); self._update_destination()
        self.name_edit.setFocus(); self.name_edit.selectAll()

    def _default_name(self):
        name, number = '新项目', 1
        while (self.location / name).exists() or (self.location / name).is_symlink():
            number += 1
            name = '新项目 ' + str(number)
        return name

    def _update_destination(self):
        entered_name = self.name_edit.text()
        name = entered_name if entered_name.strip() else self._default_name()
        self._resolved_name = name
        try:
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
    def __init__(self, info=None, parent=None, action='create'):
        super().__init__(parent)
        self.info = info
        self.kind = 'project' if info else action
        title, hint = (('打开项目', '选择图片或项目文件夹') if action == 'open'
                       else ('新建项目', '选择项目保存的位置'))
        if info:
            title = info['name']; hint = '' if info['available'] else '位置不可用'
        self.hint = hint
        self.setText(title)
        self.setFixedSize(300, 284)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setMouseTracking(True)
        self.cover = QtGui.QPixmap(info['cover']) if info and info.get('cover') else QtGui.QPixmap()
        self.setAccessibleName(title)
        self.setToolTip(info['root'] if info else hint)
        if info and not info['available']: self.setEnabled(False)

    def sizeHint(self):
        return QtCore.QSize(300, 284)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1)
        active = self.isEnabled() and (self.underMouse() or self.hasFocus())
        painter.setPen(QtGui.QPen(QtGui.QColor('#77b2fa') if active else QtGui.QColor(255, 255, 255, 240), 2 if active else 1))
        material = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
        material.setColorAt(0, QtGui.QColor(255, 255, 255, 225))
        material.setColorAt(1, QtGui.QColor(250, 250, 250, 155))
        painter.setBrush(material)
        painter.drawRoundedRect(rect, 18, 18)
        preview = QtCore.QRectF(12, 12, self.width() - 24, 200)
        path = QtGui.QPainterPath(); path.addRoundedRect(preview, 9, 9)
        painter.save(); painter.setClipPath(path)
        tint = QtGui.QLinearGradient(preview.topLeft(), preview.bottomRight())
        tint.setColorAt(0, QtGui.QColor(230, 230, 230, 150))
        tint.setColorAt(1, QtGui.QColor(245, 245, 245, 90))
        painter.fillRect(preview, tint)
        if not self.cover.isNull():
            scaled = self.cover.scaled(int(preview.width()), int(preview.height()),
                                      QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation)
            painter.drawPixmap(int(preview.x() + (preview.width() - scaled.width()) / 2),
                               int(preview.y() + (preview.height() - scaled.height()) / 2), scaled)
        else:
            painter.setPen(QtGui.QPen(QtGui.QColor('#86868b'), 1.7))
            center = preview.center()
            if self.kind != 'create':
                folder = QtCore.QRectF(center.x() - 28, center.y() - 17, 56, 38)
                painter.setBrush(QtGui.QColor(255, 255, 255, 140))
                painter.drawRoundedRect(folder, 5, 5)
                painter.drawLine(QtCore.QPointF(folder.x() + 10, folder.y() + 11),
                                 QtCore.QPointF(folder.right() - 10, folder.y() + 11))
                if self.kind == 'open':
                    painter.drawLine(center + QtCore.QPointF(15, 15), center + QtCore.QPointF(36, -6))
                    painter.drawLine(center + QtCore.QPointF(24, -6), center + QtCore.QPointF(36, -6))
                    painter.drawLine(center + QtCore.QPointF(36, -6), center + QtCore.QPointF(36, 6))
            else:
                painter.drawEllipse(center, 24, 24)
                painter.drawLine(center + QtCore.QPointF(-9, 0), center + QtCore.QPointF(9, 0))
                painter.drawLine(center + QtCore.QPointF(0, -9), center + QtCore.QPointF(0, 9))
        painter.restore()
        font = QtGui.QFont(self.font()); font.setPointSize(11); font.setBold(True)
        painter.setFont(font); painter.setPen(QtGui.QColor('#1d1d1f'))
        painter.drawText(QtCore.QRect(18, 224, self.width() - 36, 25), QtCore.Qt.AlignVCenter,
                         painter.fontMetrics().elidedText(self.text(), QtCore.Qt.ElideRight, self.width() - 36))
        if self.hint:
            font.setPointSize(9); font.setBold(False); painter.setFont(font)
            painter.setPen(QtGui.QColor('#6e6e73' if self.isEnabled() else '#98989d'))
            painter.drawText(QtCore.QRect(18, 255, self.width() - 36, 18), QtCore.Qt.AlignVCenter, self.hint)


class WorkspaceHome(QtWidgets.QWidget):
    workspace_requested = QtCore.pyqtSignal(str)
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
        title = QtWidgets.QLabel('项目'); title.setFont(QtGui.QFont(self.font().family(), 26, QtGui.QFont.Bold))
        layout.addWidget(title); layout.addSpacing(24)
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
        for action, info in [('create', None), ('open', None)] + [('project', info) for info in infos]:
            card = WorkspaceCard(info, self.content, action=action)
            if info:
                card.clicked.connect(lambda checked=False, root=info['root']: self.workspace_requested.emit(root))
                card.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
                card.customContextMenuRequested.connect(
                    lambda pos, widget=card, root=info['root']: self._show_context_menu(root, widget.mapToGlobal(pos)))
            else: card.clicked.connect(self.select_workspace if action == 'open' else self.create_workspace)
            self.cards.append(card)
        self._arrange()

    def _arrange(self):
        columns = max(1, min(5, (self.scroll.viewport().width() + 20) // 320))
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
        location = QtWidgets.QFileDialog.getExistingDirectory(self, '选择项目保存的位置', str(Path.home()))
        if not location: return
        dialog = CreateProjectDialog(location, self)
        accepted = dialog.exec_() == dialog.Accepted
        name = dialog.name_edit.text(); dialog.deleteLater()
        if not accepted: return
        try: root = self.store.create(location, name)
        except (OSError, ValueError) as exc:
            QtWidgets.QMessageBox.warning(self, '无法创建项目', str(exc)); return
        self.refresh(); self.workspace_requested.emit(str(root))

    def select_workspace(self):
        location = QtWidgets.QFileDialog.getExistingDirectory(self, '选择图片或项目文件夹', str(Path.home()))
        if not location: return
        try: info = self.store.read_existing(location)
        except (OSError, ValueError, RuntimeError) as exc:
            QtWidgets.QMessageBox.warning(self, '无法打开项目', str(exc)); return
        # The controller registers only after task and unsaved-work guards pass.
        self.workspace_requested.emit(info['root'])
