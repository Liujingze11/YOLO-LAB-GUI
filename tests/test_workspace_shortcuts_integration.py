import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import unittest
from unittest.mock import patch

from PyQt5 import QtCore, QtGui, QtTest, QtWidgets


class UnifiedShortcutsIntegrationTests(unittest.TestCase):
    def setUp(self):
        from tests.model_development.test_integration import IntegrationTests
        IntegrationTests.setUpClass()
        self.fixture = IntegrationTests()
        self.fixture.start_home = True
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.window = self.fixture.window
        self.app = self.fixture.app
        self.controller = self.fixture.controller()

    def dialog(self, key=None):
        dialog = self.controller.create_shortcut_dialog(key)
        self.addCleanup(dialog.deleteLater)
        return dialog

    def test_fresh_settings_keep_default_annotation_commands_after_reload(self):
        settings_file = Path(self.window.software_config_file)
        initial = 'software:\n  language: en\n'
        settings_file.write_text(initial)
        self.window.reload_cfg()
        self.controller.show_screening()
        dialog = self.dialog('annotation')
        self.assertIn('actionPolygon', dialog.editors['annotation'])
        self.assertEqual(dialog.editors['annotation']['actionPolygon'].keySequence().toString(), 'C')
        self.assertTrue(self.window.actionPolygon.shortcut().isEmpty())
        dialog.editors['annotation']['actionPolygon'].setKeySequence(QtGui.QKeySequence('F8'))
        self.assertTrue(dialog.save_current())
        self.window.reload_cfg()
        self.assertTrue(self.window.actionPolygon.shortcut().isEmpty())
        self.controller.show_annotation()
        self.assertEqual(self.window.actionPolygon.shortcut().toString(), 'F8')

    def test_global_entry_is_visible_on_home_and_every_workspace(self):
        c = self.controller
        self.assertIsNotNone(self.window.menuWidget(), 'global commands belong to the custom title bar')
        self.assertIs(c.shortcut_button.parent(), self.window.menuWidget())
        self.assertTrue(c.shortcut_button.isVisible())
        before = c.shortcut_button.mapTo(self.window, QtCore.QPoint())
        for switch in (c.show_screening, c.show_annotation, c.show_development, c.workspace_home.show_home):
            switch()
            self.app.processEvents()
            self.assertTrue(c.shortcut_button.isVisible())
            self.assertEqual(c.shortcut_button.mapTo(self.window, QtCore.QPoint()), before)
        self.assertFalse(hasattr(c.screening_widget, 'shortcut_button'))

    def test_existing_menu_entries_open_one_dialog_on_the_matching_page(self):
        c = self.controller
        c.show_screening()
        c.screening_widget.settings_action.trigger()
        dialog = c._shortcut_dialog
        self.assertTrue(dialog.isVisible())
        self.assertEqual(dialog.pages[dialog.tabs.currentIndex()].key, 'screening')
        self.window.shortcut()
        self.assertIs(c._shortcut_dialog, dialog)
        self.assertEqual(dialog.pages[dialog.tabs.currentIndex()].key, 'annotation')
        dialog.reject()
        c.show_development()
        c.shortcut_button.click()
        self.assertEqual(c._shortcut_dialog.pages[c._shortcut_dialog.tabs.currentIndex()].key, 'development')
        c._shortcut_dialog.reject()

    def test_title_bar_close_preserves_unsaved_annotation_cancel(self):
        self.controller.show_annotation()
        self.window.saved = False
        prompts = []

        def cancel():
            box = self.app.activeModalWidget()
            if isinstance(box, QtWidgets.QMessageBox):
                prompts.append(box.windowTitle())
                box.button(QtWidgets.QMessageBox.Cancel).click()

        QtCore.QTimer.singleShot(20, cancel)
        self.controller.title_bar.close_button.click()
        self.assertEqual(prompts, ['未保存的标注'])
        self.assertTrue(self.window.isVisible())
        self.assertFalse(self.window.saved)

    def test_editing_inactive_annotation_preserves_isolation_and_reload(self):
        c = self.controller
        c.show_screening()
        dialog = self.dialog('annotation')
        dialog.editors['annotation']['actionPolygon'].setKeySequence(QtGui.QKeySequence('F8'))
        self.assertTrue(dialog.save_current())
        self.assertTrue(self.window.actionPolygon.shortcut().isEmpty())
        self.window.reload_cfg()
        self.assertTrue(self.window.actionPolygon.shortcut().isEmpty())
        c.show_annotation()
        self.assertEqual(self.window.actionPolygon.shortcut().toString(), 'F8')
        self.window.reload_cfg()
        self.assertEqual(self.window.actionPolygon.shortcut().toString(), 'F8')
        c.show_screening()
        self.assertTrue(self.window.actionPolygon.shortcut().isEmpty())

    def test_lazy_workspaces_and_recreated_pages_use_saved_bindings(self):
        c = self.controller
        self.assertIsNone(c.screening_widget)
        self.assertIsNone(c.widget)
        dialog = self.dialog('screening')
        dialog.editors['screening']['fit'].setKeySequence(QtGui.QKeySequence('F8'))
        self.assertTrue(dialog.save_current())
        dialog.select_page('development')
        dialog.editors['development']['run'].setKeySequence(QtGui.QKeySequence('F8'))
        self.assertTrue(dialog.save_current())
        c.show_screening()
        self.assertEqual(c.screening_widget.command_actions['fit'].shortcut().toString(), 'F8')
        c.show_development()
        self.assertEqual(c.widget._start_shortcut.key().toString(), 'F8')
        c.workspace_home._reset_workbench()
        c.show_screening()
        c.show_development()
        self.assertEqual(c.screening_widget.command_actions['fit'].shortcut().toString(), 'F8')
        self.assertEqual(c.widget._start_shortcut.key().toString(), 'F8')

    def test_legacy_annotation_preferences_are_shown_even_when_actions_suspended(self):
        self.window.cfg['shortcut']['actionPolygon']['key'] = 'F8'
        self.window.load_actions_shortcut()
        self.assertTrue(self.window.actionPolygon.shortcut().isEmpty())
        dialog = self.dialog('annotation')
        self.assertEqual(dialog.editors['annotation']['actionPolygon'].keySequence().toString(), 'F8')

    def test_annotation_conflict_reserved_digits_and_disk_failure_do_not_apply(self):
        c = self.controller
        c.show_annotation()
        dialog = self.dialog('annotation')
        editor = dialog.editors['annotation']['actionPolygon']
        for key in ('D', '1'):
            editor.setKeySequence(QtGui.QKeySequence(key))
            self.assertFalse(dialog.save_current())
            self.assertEqual(self.window.actionPolygon.shortcut().toString(), 'C')
        editor.setKeySequence(QtGui.QKeySequence('F8'))
        with patch('yolo_backprop.shortcuts.os.replace', side_effect=OSError('无法写入')):
            self.assertFalse(dialog.save_current())
        self.assertEqual(self.window.actionPolygon.shortcut().toString(), 'C')
        self.assertFalse((Path(self.fixture.temp.name) / 'screening-config/annotation-shortcuts.json').exists())

    def test_saved_development_key_triggers_only_in_development(self):
        c = self.controller
        c.show_development()
        dialog = self.dialog('development')
        dialog.editors['development']['run'].setKeySequence(QtGui.QKeySequence('F8'))
        self.assertTrue(dialog.save_current())
        with patch.object(c.widget.train_tab, '_on_start_train') as run:
            self.window.activateWindow()
            c.widget.train_tab.tr_data_yaml.setFocus()
            self.app.processEvents()
            QtTest.QTest.keyClick(c.widget.train_tab.tr_data_yaml, QtCore.Qt.Key_F8)
            self.assertEqual(run.call_count, 1)
            c.show_screening()
            c.screening_widget.grid.setFocus()
            self.app.processEvents()
            QtTest.QTest.keyClick(c.screening_widget.grid, QtCore.Qt.Key_F8)
            self.assertEqual(run.call_count, 1)
