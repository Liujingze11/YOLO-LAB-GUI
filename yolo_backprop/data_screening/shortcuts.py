"""Validated, persistent shortcuts for the screening workspace."""
from PyQt5 import QtGui, QtWidgets
from yolo_backprop.shortcuts import ShortcutSettings as WorkspaceShortcutSettings


COMMANDS = {
    'rename': ('重命名', 'F2'),
    'remove': ('移入回收站', 'Delete'),
    'save': ('保存筛选', 'Ctrl+S'),
    'trash': ('打开回收站', 'Ctrl+Shift+T'),
    'copy_path': ('复制图片路径', 'Ctrl+Shift+C'),
    'open_folder': ('打开所在文件夹', 'Ctrl+Shift+O'),
    'previous': ('上一张', 'Left'),
    'next': ('下一张', 'Right'),
    'fit': ('适应窗口', 'F'),
    'compare': ('打开对比区（拖入图片）', 'C'),
    'exit_compare': ('退出对比', 'Esc'),
    'select_all': ('全选图片', 'Ctrl+A'),
}
DEFAULT_BINDINGS = {key: value[1] for key, value in COMMANDS.items()}


class ShortcutSettings(WorkspaceShortcutSettings):
    def __init__(self, path=None):
        super().__init__(COMMANDS, 'screening-shortcuts.json', path=path)


class ShortcutDialog(QtWidgets.QDialog):
    def __init__(self, bindings, save, parent=None):
        super().__init__(parent)
        self.setWindowTitle('数据筛选快捷键')
        self._save = save
        self.editors = {}
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel('点击输入框后按下新快捷键；清空可禁用。保存后立即生效。'))
        form = QtWidgets.QFormLayout()
        for key, (label, default) in COMMANDS.items():
            editor = QtWidgets.QKeySequenceEdit(QtGui.QKeySequence(bindings[key]), self)
            self.editors[key] = editor
            form.addRow(label, editor)
        layout.addLayout(form)
        self.error = QtWidgets.QLabel(''); self.error.setWordWrap(True)
        self.error.setStyleSheet('color: #a72a2a')
        layout.addWidget(self.error)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.RestoreDefaults)
        buttons.button(buttons.Save).setText('保存')
        buttons.button(buttons.Cancel).setText('取消')
        buttons.button(buttons.RestoreDefaults).setText('恢复默认')
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        buttons.button(buttons.RestoreDefaults).clicked.connect(self.restore_defaults)
        layout.addWidget(buttons)
        self.resize(470, 520)

    def restore_defaults(self):
        for key, editor in self.editors.items(): editor.setKeySequence(QtGui.QKeySequence(DEFAULT_BINDINGS[key]))
        self.error.clear()

    def accept(self):
        try:
            self._save({key: editor.keySequence().toString(QtGui.QKeySequence.PortableText)
                        for key, editor in self.editors.items()})
        except (OSError, ValueError) as exc:
            self.error.setText(str(exc)); return
        super().accept()
