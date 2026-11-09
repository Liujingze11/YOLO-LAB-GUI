"""Shared shortcut validation and atomic per-workspace preferences."""
import json
import os
from pathlib import Path
import tempfile

from PyQt5 import QtCore, QtGui, QtWidgets


class ShortcutSettings:
    def __init__(self, commands, filename, path=None, bindings=None, reserved=()):
        self.commands = commands
        self.defaults = {key: value[1] for key, value in commands.items()}
        self.reserved = set(reserved)
        base = os.environ.get('YOLO_BACKPROP_CONFIG_DIR')
        if not base:
            base = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'yolo-backprop'
        self.path = Path(path) if path is not None else Path(base) / filename
        self.bindings = dict(self.defaults)
        # Legacy annotation preferences may contain conflicts. Keep them visible
        # for correction rather than silently resetting a user's existing keys.
        if bindings:
            self.bindings.update({key: value for key, value in bindings.items()
                                  if key in commands and isinstance(value, str)})
        try:
            document = json.loads(self.path.read_text(encoding='utf-8'))
            self.bindings = self.validate(document['bindings'])
        except (OSError, ValueError, KeyError, TypeError):
            pass  # Never overwrite a damaged file just by opening settings.

    def validate(self, updates):
        if not isinstance(updates, dict) or set(updates) - set(self.commands):
            raise ValueError('快捷键配置包含未知操作')
        values = dict(self.bindings)
        values.update(updates)
        seen = {}
        for key, value in values.items():
            label = self.commands[key][0]
            if not isinstance(value, str): raise ValueError('快捷键必须是文本')
            if not value.strip():
                values[key] = ''
                continue
            sequence = QtGui.QKeySequence.fromString(value, QtGui.QKeySequence.PortableText)
            normalized = sequence.toString(QtGui.QKeySequence.PortableText)
            if (not normalized or sequence.count() != 1
                    or (int(sequence[0]) & 0x01ffffff) in (0, int(QtCore.Qt.Key_unknown))):
                raise ValueError('请使用单个按键或组合键：' + label)
            if normalized in self.reserved:
                raise ValueError('数字 0–9 用于选择标注类别，请使用其他快捷键：' + label)
            if normalized in seen:
                raise ValueError(label + '与' + self.commands[seen[normalized]][0]
                                 + '使用了相同快捷键：' + normalized)
            seen[normalized] = key
            values[key] = normalized
        return values

    def save(self, updates):
        values = self.validate(updates)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix='.' + self.path.stem + '-', dir=self.path.parent)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                json.dump({'version': 1, 'bindings': values}, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
        self.bindings = values
        return dict(values)


def annotation_settings(window):
    commands, bindings = {}, {}
    configured = window.cfg.setdefault('shortcut', {})
    for key, default in getattr(window, '_annotation_shortcut_defaults', {}).items():
        configured.setdefault(key, {'default_key': default, 'key': default})
    # Keep the common annotation workflow first instead of YAML's alphabetical
    # serialization order; include other configured actions after it.
    order = ('actionImages_dir', 'actionLabel_dir', 'actionPrev_image', 'actionNext_image',
             'actionSave', 'actionPolygon', 'actionSegment_anything_point',
             'actionSegment_anything_box', 'actionRepaint', 'actionBackspace',
             'actionFinish', 'actionCancel', 'actionEdit', 'actionDelete', 'actionCopy',
             'actionTo_top', 'actionTo_bottom', 'actionUnion', 'actionSubtract',
             'actionIntersect', 'actionExclude', 'actionPrev_group', 'actionNext_group',
             'actionVisible', 'actionBit_map', 'actionZoom_in', 'actionZoom_out',
             'actionFit_window', 'actionScene_shot', 'actionWindow_shot')
    keys = [key for key in order if key in configured]
    keys.extend(key for key in configured if key not in keys)
    for key in keys:
        value = configured[key]
        action = getattr(window, key, None)
        if not isinstance(action, QtWidgets.QAction): continue
        commands[key] = (action.text().replace('&', ''), value.get('default_key') or '')
        bindings[key] = value.get('key') or ''
    return ShortcutSettings(commands, 'annotation-shortcuts.json', bindings=bindings,
                            reserved=tuple(str(i) for i in range(10)))


def development_settings():
    return ShortcutSettings({'run': ('运行当前训练 / 推理', 'Ctrl+Return')},
                            'development-shortcuts.json')
