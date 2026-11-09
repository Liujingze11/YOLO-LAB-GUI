import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PyQt5 import QtGui, QtWidgets


class WorkspaceShortcutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'shortcuts.json'

    def settings(self, **kwargs):
        from yolo_backprop.shortcuts import ShortcutSettings
        return ShortcutSettings({'run': ('运行', 'F5'), 'stop': ('停止', 'F6')},
                                'shortcuts.json', path=self.path, **kwargs)

    def test_legacy_values_are_preserved_then_saved_values_take_precedence(self):
        settings = self.settings(bindings={'run': 'Ctrl+R'})
        self.assertEqual(settings.bindings['run'], 'Ctrl+R')
        settings.save({'run': 'F8', 'stop': ''})
        reloaded = self.settings(bindings={'run': 'Ctrl+R'})
        self.assertEqual(reloaded.bindings, {'run': 'F8', 'stop': ''})

    def test_conflicts_invalid_keys_and_reserved_keys_leave_file_unchanged(self):
        settings = self.settings(reserved=('0', '1'))
        settings.save({'run': 'F8'})
        before = self.path.read_bytes()
        for value in ('F6', '1', 'NotAKey', 'Ctrl+K, Ctrl+R'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                settings.save({'run': value})
            self.assertEqual(self.path.read_bytes(), before)
            self.assertEqual(settings.bindings['run'], 'F8')

    def test_atomic_save_failure_keeps_previous_file_and_live_bindings(self):
        settings = self.settings()
        settings.save({'run': 'F8'})
        before = self.path.read_bytes()
        with patch('yolo_backprop.shortcuts.os.replace', side_effect=OSError('只读目录')):
            with self.assertRaises(OSError): settings.save({'run': 'F9'})
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(settings.bindings['run'], 'F8')
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def dialog(self):
        from yolo_backprop.shortcuts import ShortcutSettings
        from yolo_backprop.widgets.workspace_shortcuts_dialog import ShortcutPage, WorkspaceShortcutsDialog
        a = self.settings()
        b = ShortcutSettings({'fit': ('适应窗口', 'F')}, 'second.json',
                             path=self.path.with_name('second.json'))
        dialog = WorkspaceShortcutsDialog([
            ShortcutPage('screening', '数据筛选', a, a.save),
            ShortcutPage('annotation', '数据标注', b, b.save)], 'screening')
        self.addCleanup(dialog.deleteLater)
        return dialog, a, b

    def test_page_drafts_survive_switching_and_only_current_page_is_saved(self):
        dialog, a, b = self.dialog()
        dialog.editors['screening']['run'].setKeySequence(QtGui.QKeySequence('F8'))
        dialog.tabs.setCurrentIndex(1)
        dialog.editors['annotation']['fit'].setKeySequence(QtGui.QKeySequence('F8'))
        self.assertTrue(dialog.save_current())  # Same key across pages is valid.
        self.assertEqual(b.bindings['fit'], 'F8')
        self.assertFalse(a.path.exists())
        dialog.tabs.setCurrentIndex(0)
        self.assertEqual(dialog.editors['screening']['run'].keySequence().toString(), 'F8')
        self.assertTrue(dialog.save_current())
        self.assertEqual(a.bindings['run'], 'F8')

    def test_defaults_are_a_draft_and_only_affect_the_selected_page(self):
        dialog, a, b = self.dialog()
        dialog.editors['screening']['run'].setKeySequence(QtGui.QKeySequence('F8'))
        dialog.save_current()
        dialog.tabs.setCurrentIndex(1)
        dialog.editors['annotation']['fit'].clear()
        dialog.restore_defaults()
        self.assertEqual(dialog.editors['annotation']['fit'].keySequence().toString(), 'F')
        self.assertEqual(dialog.editors['screening']['run'].keySequence().toString(), 'F8')
        dialog.tabs.setCurrentIndex(0)
        dialog.restore_defaults()
        self.assertEqual(a.bindings['run'], 'F8')
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.Discard):
            dialog.reject()
        self.assertEqual(a.bindings['run'], 'F8')

    def test_invalid_page_keeps_dialog_open_and_reports_conflict(self):
        dialog, a, b = self.dialog()
        dialog.show()
        dialog.editors['screening']['run'].setKeySequence(QtGui.QKeySequence('F6'))
        self.assertFalse(dialog.save_current())
        self.assertTrue(dialog.isVisible())
        self.assertIn('相同快捷键', dialog.status.text())
        self.assertFalse(a.path.exists())
        dialog.done(QtWidgets.QDialog.Rejected)

    def test_close_can_return_to_unsaved_drafts(self):
        dialog, a, b = self.dialog()
        dialog.show()
        dialog.editors['screening']['run'].clear()
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.Cancel):
            dialog.reject()
        self.assertTrue(dialog.isVisible())
        self.assertFalse(a.path.exists())
        dialog.done(QtWidgets.QDialog.Rejected)
