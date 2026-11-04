import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from PIL import Image
from PyQt5 import QtCore, QtGui, QtWidgets, QtTest


class ScreeningWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        from ISAT.data_screening.widget import DataScreeningWidget
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        config = patch.dict(os.environ, {'YOLO_BACKPROP_CONFIG_DIR': str(Path(self.temp.name) / 'config')})
        config.start(); self.addCleanup(config.stop)
        self.root = Path(self.temp.name) / '图片 文件夹'; self.root.mkdir()
        Image.new('RGB', (320, 240), 'red').save(self.root / 'a.png')
        Image.new('RGB', (320, 240), 'blue').save(self.root / 'b.png')
        self.original_root = self.root
        from ISAT.data_screening.workspace import WorkspaceSettings
        WorkspaceSettings().select(Path(self.temp.name) / 'workspace')
        self.page = DataScreeningWidget()
        self.purge_prompt = patch.object(self.page, '_confirm_purge', return_value=False)
        self.purge_prompt.start(); self.addCleanup(self.purge_prompt.stop)
        self.page.resize(1100, 750); self.page.show(); self.app.processEvents()
        self.addCleanup(self.cleanup_page)

    def cleanup_page(self):
        self.page.stop_workers()
        for worker in self.page.active_workers(): worker.wait(10000)
        self.app.processEvents()
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.Discard):
            self.page.close()

    def wait(self, predicate, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                self.app.processEvents()
                if predicate(): break
            time.sleep(.01)
        self.assertTrue(predicate(), 'UI operation did not finish')

    def load(self):
        self.page.open_folder(str(self.root))
        self.wait(lambda: self.page.session is not None and not self.page.active_workers())
        self.root = self.page.session.root

    def test_drop_folder_populates_grid_and_large_preview(self):
        mime = QtCore.QMimeData(); mime.setUrls([QtCore.QUrl.fromLocalFile(str(self.root))])
        enter = QtGui.QDragEnterEvent(QtCore.QPoint(50, 50), QtCore.Qt.CopyAction, mime, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        drop = QtGui.QDropEvent(QtCore.QPointF(50, 50), QtCore.Qt.CopyAction, mime, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        QtWidgets.QApplication.sendEvent(self.page, enter)
        self.assertTrue(enter.isAccepted())
        QtWidgets.QApplication.sendEvent(self.page, drop)
        self.wait(lambda: self.page.session is not None and not self.page.active_workers())
        self.assertEqual(self.page.grid.count(), 2)
        self.assertEqual(self.page.preview.displayed_path, str(self.page.session.root / 'a.png'))

    def test_right_click_action_moves_thumbnail_to_bottom_strip_and_double_click_restores(self):
        self.load()
        original = {p.name: p.read_bytes() for p in self.original_root.iterdir()}
        row = self.page.grid.item(0); asset = row.data(QtCore.Qt.UserRole)
        icon = row.icon().cacheKey()
        menu = self.page.create_context_menu()
        remove = self.page.command_actions['remove']
        self.assertIn(remove, menu.actions()); remove.trigger(); menu.deleteLater()
        strip = self.page.trash_list
        self.assertEqual(strip.count(), 1)
        self.assertEqual(strip.item(0).data(QtCore.Qt.UserRole), asset)
        self.assertEqual(strip.item(0).icon().cacheKey(), icon)
        self.assertEqual(self.page.grid.count(), 1)
        left = self.page.splitter.widget(0)
        self.assertTrue(left.isAncestorOf(strip) and left.isAncestorOf(self.page.grid))
        self.assertGreater(strip.mapTo(left, QtCore.QPoint()).y(), self.page.grid.geometry().bottom())
        self.assertFalse(strip.isWrapping())
        self.assertNotIn('重命名', [b.text() for b in self.page.findChildren(QtWidgets.QPushButton)])
        self.assertNotIn('移入回收站', [b.text() for b in self.page.findChildren(QtWidgets.QPushButton)])
        self.assertFalse(any(label.text().startswith('工作空间：') for label in self.page.findChildren(QtWidgets.QLabel)))
        self.app.processEvents()
        center = strip.visualItemRect(strip.item(0)).center()
        QtTest.QTest.mouseClick(strip.viewport(), QtCore.Qt.LeftButton, pos=center)
        QtTest.QTest.mouseDClick(strip.viewport(), QtCore.Qt.LeftButton, pos=center)
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(strip.count(), 0)
        self.assertEqual(self.page.grid.count(), 2)
        self.assertEqual({p.name: p.read_bytes() for p in self.original_root.iterdir()}, original)

    def test_saved_trash_reopens_with_real_thumbnail_and_purge_clears_strip(self):
        self.load(); self.page.command_actions['remove'].trigger()
        self.page.save_button.click(); self.wait(lambda: not self.page._busy)
        project = self.page.session.project_root
        self.page.open_folder(str(project), project=True)
        self.wait(lambda: not self.page.active_workers() and not self.page._busy)
        strip = self.page.trash_list
        self.assertEqual(strip.count(), 1)
        image = strip.item(0).icon().pixmap(72, 54).toImage()
        self.assertEqual(image.pixelColor(image.rect().center()).name(), '#ff0000')
        with patch.object(self.page, '_confirm_purge', return_value=True):
            self.page.save_button.click(); self.wait(lambda: not self.page._busy)
        self.assertEqual(strip.count(), 0)
        self.assertEqual(self.page.session.trash, [])
        self.assertTrue((self.original_root / 'a.png').is_file())

    def test_inline_restore_is_guarded_while_busy_and_can_restore_multiple_photos(self):
        self.load(); self.page.grid.selectAll(); self.page.command_actions['remove'].trigger()
        strip = self.page.trash_list; strip.selectAll(); self.app.processEvents()
        self.assertEqual(strip.count(), 2)
        self.assertEqual(strip.visualItemRect(strip.item(0)).y(), strip.visualItemRect(strip.item(1)).y())
        self.assertTrue(self.page.trash_restore_button.isEnabled())
        self.page._set_busy(True)
        self.page.trash_restore_button.click()
        self.page.restore_items([row.data(QtCore.Qt.UserRole) for row in strip.selectedItems()])
        self.assertEqual(strip.count(), 2)
        self.page._set_busy(False)
        self.page.trash_restore_button.click()
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(strip.count(), 0)
        self.assertEqual(self.page.grid.count(), 2)

    def test_trash_focus_does_not_delete_or_rename_a_retained_photo(self):
        self.load(); self.page.command_actions['remove'].trigger()
        self.assertEqual(self.page.grid.count(), 1)
        strip = self.page.trash_list
        strip.setCurrentRow(0); self.page.activateWindow(); strip.setFocus(); self.app.processEvents()
        with patch.object(QtWidgets.QInputDialog, 'getText') as rename:
            QtTest.QTest.keyClick(strip, QtCore.Qt.Key_Delete)
            QtTest.QTest.keyClick(strip, QtCore.Qt.Key_F2)
            self.page.command_actions['remove'].trigger()
            self.page.command_actions['rename'].trigger()
        rename.assert_not_called()
        self.assertEqual([item.name for item in self.page.session.items], ['b.png'])
        self.assertEqual(strip.count(), 1)

    def test_rename_and_multiselect_delete_preserve_original_files(self):
        self.load(); self.page.grid.setCurrentRow(0)
        with patch.object(QtWidgets.QInputDialog, 'getText', return_value=('保留图片', True)):
            self.page.command_actions['rename'].trigger()
        self.assertEqual(self.page.session.items[0].name, '保留图片.png')
        self.assertEqual(self.page.grid.item(0).text(), '保留图片.png')
        self.page.grid.selectAll(); self.page.command_actions['remove'].trigger()
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.grid.count(), 0)
        self.assertEqual(self.page.session.items, [])
        self.assertIsNone(self.page.preview.displayed_path)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['a.png', 'b.png'])

    def test_export_button_creates_project_and_emits_ready_paths(self):
        self.load(); self.page.grid.setCurrentRow(1); self.page.command_actions['remove'].trigger()
        received = []; self.page.project_ready.connect(received.append)
        with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=self.temp.name):
            self.page.import_button.click()
        self.wait(lambda: bool(received) and not self.page.active_workers())
        result = received[0]
        self.assertEqual(result['files'], ['a.png'])
        self.assertTrue((Path(result['image_root']) / 'a.png').is_file())
        self.assertTrue(Path(result['label_root']).is_dir())
        self.assertFalse(list(Path(result['label_root']).glob('*.json')))
        self.assertTrue((self.original_root / 'b.png').is_file())

    def test_quick_selection_changes_do_not_leave_old_preview(self):
        self.load()
        self.page.grid.setCurrentRow(0); self.app.processEvents()
        self.page.grid.setCurrentRow(1)
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.preview.displayed_path, str(self.root / 'b.png'))

    def test_import_cancel_guard_creates_nothing(self):
        self.load(); self.page.before_import = lambda: False
        self.page.import_button.click(); self.app.processEvents()
        self.assertFalse((self.root.parent / (self.root.name + '_筛选')).exists())
        self.assertFalse(self.page.active_workers())

    def test_cancel_ignores_queued_scan_result_and_does_not_start_a_new_preview(self):
        self.page.open_folder(str(self.root))
        self.assertTrue(self.page._scan_worker.wait(10000))
        # Its result is queued while the GUI has not processed events yet.
        self.page.stop_workers()
        self.app.processEvents(); self.app.processEvents()
        self.assertIsNone(self.page.session)
        self.assertFalse(self.page.active_workers())

    def test_thumbnail_grid_keeps_three_columns_when_left_pane_is_resized(self):
        Image.new('RGB', (80, 60), 'green').save(self.root / 'c.png')
        Image.new('RGB', (80, 60), 'yellow').save(self.root / 'd.png')
        self.load(); self.page.resize(1450, 850)
        for width in (650, 390):
            self.page.splitter.setSizes([width, 1450 - width])
            self.app.processEvents(); self.page.grid.doItemsLayout(); self.app.processEvents()
            rectangles = [self.page.grid.visualItemRect(self.page.grid.item(i)) for i in range(4)]
            self.assertEqual(rectangles[0].y(), rectangles[2].y())
            self.assertGreater(rectangles[3].y(), rectangles[0].y())

    def test_dragging_other_thumbnail_preserves_main_photo_and_creates_equal_comparison(self):
        self.load()
        self.page.grid.drag_anchor_requested.emit()
        self.page.grid.setCurrentRow(1)
        self.page.grid.image_drag_started.emit()
        mime = self.page.grid.mimeData([self.page.grid.item(1)])
        edge = self.page.preview.viewport().width() - 20
        enter = QtGui.QDragEnterEvent(QtCore.QPoint(edge, 30), QtCore.Qt.CopyAction, mime, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        drop = QtGui.QDropEvent(QtCore.QPointF(edge, 30), QtCore.Qt.CopyAction, mime, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        QtWidgets.QApplication.sendEvent(self.page.preview.viewport(), enter)
        self.assertTrue(enter.isAccepted())
        QtWidgets.QApplication.sendEvent(self.page.preview.viewport(), drop)
        self.page.grid.image_drag_finished.emit(True)
        self.wait(lambda: not self.page.active_workers() and self.page.comparison_preview.displayed_path is not None)
        self.assertEqual(self.page.preview.displayed_path, str(self.root / 'a.png'))
        self.assertEqual(self.page.comparison_preview.displayed_path, str(self.root / 'b.png'))
        self.assertLessEqual(abs(self.page.preview.width() - self.page.comparison_preview.width()), 1)
        self.page.command_actions['exit_compare'].trigger(); self.app.processEvents()
        self.assertTrue(self.page.comparison_panel.isHidden())
        self.assertEqual(self.page.preview.displayed_path, str(self.root / 'a.png'))

    def test_closing_comparison_ignores_already_queued_image_result(self):
        self.load(); self.page.compare_with(str(self.root / 'b.png'))
        self.assertTrue(self.page._comparison_worker.wait(10000))
        self.page.exit_comparison()
        self.app.processEvents(); self.app.processEvents()
        self.assertTrue(self.page.comparison_panel.isHidden())
        self.assertIsNone(self.page.comparison_preview.displayed_path)

    def test_changed_shortcut_renames_and_menu_copies_real_file_path(self):
        self.load(); self.page.update_shortcuts({'rename': 'R'})
        self.page.activateWindow(); self.page.grid.setFocus(); self.app.processEvents()
        with patch.object(QtWidgets.QInputDialog, 'getText', return_value=('新名字', True)):
            QtTest.QTest.keyClick(self.page.grid, QtCore.Qt.Key_F2); self.app.processEvents()
            self.assertEqual(self.page.session.items[0].name, 'a.png')
            QtTest.QTest.keyClick(self.page.grid, QtCore.Qt.Key_R); self.app.processEvents()
        self.assertEqual(self.page.session.items[0].name, '新名字.png')
        menu = self.page.create_context_menu()
        self.assertIn(self.page.command_actions['copy_path'], menu.actions())
        self.page.command_actions['copy_path'].trigger()
        self.assertEqual(self.app.clipboard().text(), str(self.root / 'a.png'))
        menu.deleteLater()

    def test_shortcut_dialog_updates_live_actions_and_persists_changes(self):
        dialog = self.page.create_shortcut_dialog()
        dialog.editors['rename'].setKeySequence(QtGui.QKeySequence('Ctrl+R'))
        dialog.accept()
        self.assertEqual(self.page.command_actions['rename'].shortcut().toString(), 'Ctrl+R')
        from ISAT.data_screening.shortcuts import ShortcutSettings
        self.assertEqual(ShortcutSettings().bindings['rename'], 'Ctrl+R')
        cancelled = self.page.create_shortcut_dialog()
        cancelled.restore_defaults(); cancelled.reject()
        self.assertEqual(ShortcutSettings().bindings['rename'], 'Ctrl+R')

    def test_replacing_comparison_discards_previous_queued_result(self):
        extra = self.root / 'c.png'; Image.new('RGB', (80, 60), 'green').save(extra)
        self.load(); self.page.compare_with(str(self.root / 'b.png'))
        self.assertTrue(self.page._comparison_worker.wait(10000))
        self.page.compare_with(str(extra))
        self.wait(lambda: not self.page.active_workers() and self.page.comparison_preview.displayed_path == str(extra))
        self.assertEqual(self.page.preview.displayed_path, str(self.root / 'a.png'))

    def test_navigation_shortcuts_work_with_focus_on_the_large_preview(self):
        self.load(); self.page.activateWindow(); self.page.preview.setFocus(); self.app.processEvents()
        QtTest.QTest.keyClick(self.page.preview, QtCore.Qt.Key_Right)
        self.wait(lambda: not self.page.active_workers() and self.page.preview.displayed_path == str(self.root / 'b.png'))
        QtTest.QTest.keyClick(self.page.preview, QtCore.Qt.Key_Left)
        self.wait(lambda: not self.page.active_workers() and self.page.preview.displayed_path == str(self.root / 'a.png'))

    def test_save_retains_trash_when_confirmation_declined_and_dialog_restores_it(self):
        self.load(); self.page.command_actions['remove'].trigger()
        self.assertEqual(len(self.page.session.trash), 1)
        self.assertTrue(self.page.session.trash[0].source.exists())
        self.page.save_button.click()
        self.wait(lambda: not self.page._busy)
        self.page._confirm_purge.assert_called_once()
        self.assertIn('回收站', self.page.trash_label.text())
        dialog = self.page.create_trash_dialog()
        dialog.list.selectAll(); dialog.restore_selected()
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.grid.count(), 2)
        self.assertEqual(self.page.session.trash, [])
        self.assertTrue((self.original_root / 'a.png').exists())
        dialog.deleteLater()

    def test_save_failure_never_prompts_for_purge(self):
        self.load(); self.page.command_actions['remove'].trigger()
        with patch.object(self.page.session, 'save_project', side_effect=OSError('disk full')), \
                patch.object(QtWidgets.QMessageBox, 'warning'):
            self.page.save_button.click(); self.wait(lambda: not self.page._busy)
        self.page._confirm_purge.assert_not_called()
        self.assertTrue(self.page.session.trash[0].source.exists())

    def test_cancel_workspace_selection_prevents_import(self):
        self.page.workspace = None
        with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=''):
            self.page.open_folder(str(self.original_root))
        self.assertIsNone(self.page.session)
        self.assertFalse(self.page.active_workers())

    def test_confirmed_purge_removes_copies_after_save_and_keeps_originals(self):
        self.load(); self.page.command_actions['remove'].trigger()
        with patch.object(self.page, '_confirm_purge', return_value=True):
            self.page.save_button.click(); self.wait(lambda: not self.page._busy)
        self.assertEqual(self.page.session.trash, [])
        self.assertEqual(self.page.grid.count(), 1)
        self.assertTrue((self.original_root / 'a.png').is_file())
        self.assertFalse((self.page.session.project_root / '.trash/images/a.png').exists())

    def drop_image(self, target, path, position=None, mime=None):
        mime = mime or QtCore.QMimeData()
        if not mime.hasUrls(): mime.setUrls([QtCore.QUrl.fromLocalFile(str(path))])
        position = position or target.viewport().rect().center()
        enter = QtGui.QDragEnterEvent(position, QtCore.Qt.CopyAction, mime, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        drop = QtGui.QDropEvent(QtCore.QPointF(position), QtCore.Qt.CopyAction, mime, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        self.app.sendEvent(target.viewport(), enter); self.assertTrue(enter.isAccepted())
        self.app.sendEvent(target.viewport(), drop); self.assertTrue(drop.isAccepted())
        self.wait(lambda: not self.page.active_workers())

    def test_drop_center_replaces_main_edge_adds_compare_and_each_side_replaces_independently(self):
        Image.new('RGB', (80, 60), 'green').save(self.root / 'c.png')
        self.load()
        a, b, c = [str(self.root / name) for name in ('a.png', 'b.png', 'c.png')]
        self.drop_image(self.page.preview, b)
        self.assertEqual(self.page.preview.displayed_path, b)
        self.assertTrue(self.page.comparison_panel.isHidden())
        self.drop_image(self.page.preview, a, QtCore.QPoint(self.page.preview.viewport().width() - 10, 40))
        self.assertEqual(self.page.preview.displayed_path, b)
        self.assertEqual(self.page.comparison_preview.displayed_path, a)
        self.drop_image(self.page.preview, c)
        self.assertEqual(self.page.preview.displayed_path, c)
        self.assertEqual(self.page.comparison_preview.displayed_path, a)
        self.drop_image(self.page.comparison_preview, b)
        self.assertEqual(self.page.preview.displayed_path, c)
        self.assertEqual(self.page.comparison_preview.displayed_path, b)

    def test_drag_preview_back_to_grid_promotes_other_image_without_duplicating_thumbnail(self):
        self.load(); self.page.compare_with(str(self.root / 'b.png'))
        self.wait(lambda: not self.page.active_workers())
        self.drop_image(self.page.grid, self.root / 'a.png', mime=self.page.preview.mime_data())
        self.assertEqual(self.page.preview.displayed_path, str(self.root / 'b.png'))
        self.assertTrue(self.page.comparison_panel.isHidden())
        self.assertEqual(self.page.grid.count(), 2)
        self.drop_image(self.page.grid, self.root / 'b.png', mime=self.page.preview.mime_data())
        self.assertIsNone(self.page.preview.displayed_path)
        self.assertEqual(self.page.grid.count(), 2)
        self.assertEqual(len(self.page.session.items), 2)

    def test_cancel_after_save_commit_suppresses_queued_purge_prompt_and_import(self):
        self.load(); self.page.command_actions['remove'].trigger()
        received = []; self.page.project_ready.connect(received.append)
        self.page.import_button.click()
        self.assertTrue(self.page._export_worker.wait(10000))
        self.page.stop_workers(); self.wait(lambda: not self.page._busy)
        self.page._confirm_purge.assert_not_called()
        self.assertEqual(received, [])
