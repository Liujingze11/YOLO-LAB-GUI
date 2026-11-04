"""Validated, persistent shortcuts for the screening workspace."""
import json
import os
from pathlib import Path
import tempfile

from PyQt5 import QtCore, QtGui, QtWidgets


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


class ShortcutSettings:
    def __init__(self, path=None):
        base = os.environ.get('YOLO_BACKPROP_CONFIG_DIR')
        if not base:
            base = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'yolo-backprop'
        self.path = Path(path) if path is not None else Path(base) / 'screening-shortcuts.json'
        self.bindings = dict(DEFAULT_BINDINGS)
        try:
            document = json.loads(self.path.read_text(encoding='utf-8'))
            self.bindings = self.validate(document['bindings'])
        except (OSError, ValueError, KeyError, TypeError):
            pass  # Leave a damaged file untouched until the user explicitly saves.

    def validate(self, updates):
        if not isinstance(updates, dict) or set(updates) - set(COMMANDS):
            raise ValueError('快捷键配置包含未知操作')
        values = dict(self.bindings)
        values.update(updates)
        seen = {}
        for key, value in values.items():
            if not isinstance(value, str): raise ValueError('快捷键必须是文本')
            if not value.strip():
                values[key] = ''; continue
            sequence = QtGui.QKeySequence.fromString(value, QtGui.QKeySequence.PortableText)
            normalized = sequence.toString(QtGui.QKeySequence.PortableText)
            if (not normalized or sequence.count() != 1
                    or (int(sequence[0]) & 0x01ffffff) in (0, int(QtCore.Qt.Key_unknown))):
                raise ValueError('请使用单个按键或组合键：' + COMMANDS[key][0])
            if normalized in seen:
                raise ValueError(COMMANDS[key][0] + '与' + COMMANDS[seen[normalized]][0] + '使用了相同快捷键：' + normalized)
            seen[normalized] = key
            values[key] = normalized
        return values

    def save(self, updates):
        values = self.validate(updates)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix='.screening-shortcuts-', dir=self.path.parent)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                json.dump({'version': 1, 'bindings': values}, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
        self.bindings = values
        return dict(values)


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
