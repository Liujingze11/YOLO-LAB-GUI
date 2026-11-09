"""One native dialog for shortcuts belonging to independent workspaces."""
from dataclasses import dataclass
from typing import Callable

from PyQt5 import QtCore, QtGui, QtWidgets
from yolo_backprop.shortcuts import ShortcutSettings


@dataclass
class ShortcutPage:
    key: str
    title: str
    settings: ShortcutSettings
    save: Callable


class WorkspaceShortcutsDialog(QtWidgets.QDialog):
    def __init__(self, pages, current, parent=None):
        super().__init__(parent)
        self.setWindowTitle('快捷键设置')
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.pages = list(pages)
        self.editors = {}
        self._saved = {}
        self.tabs = QtWidgets.QTabWidget()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)
        hint = QtWidgets.QLabel('选择功能页面，点击输入框录入快捷键。保存当前页后生效，清空可禁用。')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        for page in self.pages:
            self.editors[page.key] = {}
            body = QtWidgets.QWidget()
            form = QtWidgets.QFormLayout(body)
            form.setContentsMargins(16, 16, 16, 16)
            form.setVerticalSpacing(10)
            form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
            note = ('数字 0–9 保留用于选择标注类别。' if page.key == 'annotation' else
                    '在训练或推理页面运行当前任务。' if page.key == 'development' else
                    '以下快捷键仅在数据筛选界面生效。')
            label = QtWidgets.QLabel(note)
            label.setWordWrap(True)
            label.setProperty('glassRole', 'muted')
            form.addRow(label)
            for key, (title, default) in page.settings.commands.items():
                editor = QtWidgets.QKeySequenceEdit(QtGui.QKeySequence(page.settings.bindings[key]))
                editor.setAccessibleName(title)
                editor.setMinimumWidth(160)
                editor.setToolTip('默认：' + (default or '未设置'))
                editor.findChild(QtWidgets.QLineEdit).setPlaceholderText('按下快捷键')
                self.editors[page.key][key] = editor
                clear = QtWidgets.QPushButton('清空')
                clear.setAutoDefault(False)
                clear.setFixedWidth(52)
                clear.setAccessibleName('清空' + title + '快捷键')
                clear.clicked.connect(editor.clear)
                field = QtWidgets.QHBoxLayout()
                field.setSpacing(8)
                field.addWidget(editor, 1)
                field.addWidget(clear)
                form.addRow(title, field)
                editor.keySequenceChanged.connect(self._refresh_status)
            scroll = QtWidgets.QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
            scroll.setWidget(body)
            # setWidget enables background filling by default, which would
            # paint a light palette behind light text when the app is dark.
            body.setAutoFillBackground(False)
            scroll.viewport().setAutoFillBackground(False)
            self.tabs.addTab(scroll, page.title)
            self._saved[page.key] = self._values(page)
        layout.addWidget(self.tabs, 1)
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        row = QtWidgets.QHBoxLayout()
        self.reset_button = QtWidgets.QPushButton('恢复当前页默认')
        self.reset_button.setAutoDefault(False)
        self.reset_button.clicked.connect(self.restore_defaults)
        row.addWidget(self.reset_button)
        row.addStretch()
        self.close_button = QtWidgets.QPushButton('关闭')
        self.close_button.setAutoDefault(False)
        self.close_button.clicked.connect(self.reject)
        row.addWidget(self.close_button)
        self.save_button = QtWidgets.QPushButton('保存当前页')
        self.save_button.setProperty('glassRole', 'primary')
        self.save_button.setAutoDefault(False)
        self.save_button.clicked.connect(self.save_current)
        row.addWidget(self.save_button)
        layout.addLayout(row)
        self.tabs.currentChanged.connect(self._refresh_status)
        self.select_page(current)
        self._refresh_status()
        self.setMinimumSize(580, 400)
        self.resize(680, 620)

    def select_page(self, key):
        for index, page in enumerate(self.pages):
            if page.key == key:
                self.tabs.setCurrentIndex(index)
                return

    def _values(self, page):
        return {key: editor.keySequence().toString(QtGui.QKeySequence.PortableText)
                for key, editor in self.editors[page.key].items()}

    def _refresh_status(self, *_):
        if not hasattr(self, 'status'): return
        page = self.pages[self.tabs.currentIndex()]
        self.status.setStyleSheet('')
        self.status.setText('当前页有未保存的修改' if self._values(page) != self._saved[page.key]
                            else '各功能的快捷键独立生效，可使用相同按键。')

    def restore_defaults(self):
        page = self.pages[self.tabs.currentIndex()]
        for key, editor in self.editors[page.key].items():
            editor.setKeySequence(QtGui.QKeySequence(page.settings.defaults[key]))
        self._refresh_status()

    def save_current(self):
        page = self.pages[self.tabs.currentIndex()]
        try:
            values = page.settings.validate(self._values(page))
            page.save(values)
        except (OSError, ValueError) as exc:
            self.status.setStyleSheet('color: #d14747')
            self.status.setText(str(exc))
            return False
        self._saved[page.key] = self._values(page)
        self.status.setStyleSheet('')
        self.status.setText(page.title + '快捷键已保存')
        return True

    def reject(self):
        if any(self._values(page) != self._saved[page.key] for page in self.pages):
            answer = QtWidgets.QMessageBox.question(
                self, '未保存的快捷键', '有页面的修改尚未保存，是否放弃这些修改并关闭？',
                QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Cancel)
            if answer != QtWidgets.QMessageBox.Discard: return
        super().reject()
