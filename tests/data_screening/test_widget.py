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
        from yolo_backprop.data_screening.widget import DataScreeningWidget
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        config = patch.dict(os.environ, {'YOLO_BACKPROP_CONFIG_DIR': str(Path(self.temp.name) / 'config')})
        config.start(); self.addCleanup(config.stop)
        self.root = Path(self.temp.name) / '图片 文件夹'; self.root.mkdir()
        Image.new('RGB', (320, 240), 'red').save(self.root / 'a.png')
        Image.new('RGB', (320, 240), 'blue').save(self.root / 'b.png')
        self.original_root = self.root
        from yolo_backprop.data_screening.workspace import WorkspaceSettings
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

    def test_initial_state_has_one_import_entry_without_empty_work_panels(self):
        self.assertFalse(self.page.splitter.isVisible())
        self.assertTrue(self.page.empty_page.isVisible())
        buttons = [b for b in self.page.findChildren(QtWidgets.QPushButton) if b.isVisible()]
        self.assertEqual([b.text() for b in buttons], ['打开图片文件夹'])
        self.assertFalse(self.page.trash_panel.isVisible())
        self.assertFalse(self.page.previous_button.isVisible())
        self.assertFalse(self.page.status.isVisible())

    def test_import_button_reveals_aligned_work_panels_and_image_position(self):
        self.assertTrue(hasattr(self.page, 'empty_open_button'), 'empty state offers import')
        with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=str(self.root)):
            QtTest.QTest.mouseClick(self.page.empty_open_button, QtCore.Qt.LeftButton)
        self.wait(lambda: self.page.session is not None and not self.page.active_workers())
        self.assertFalse(self.page.empty_page.isVisible())
        self.assertTrue(self.page.splitter.isVisible())
        self.assertTrue(self.page.list_header.isAncestorOf(self.page.open_button))
        self.assertEqual(self.page.position_label.text(), '1 / 2')
        self.assertEqual(self.page.grid.mapTo(self.page, QtCore.QPoint()).y(),
                         self.page.preview.mapTo(self.page, QtCore.QPoint()).y())
        self.assertFalse(self.page.grid.verticalScrollBar().isVisible())
        self.page.following_button.click()
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.position_label.text(), '2 / 2')

    def test_empty_import_card_accepts_a_folder_drop(self):
        self.assertTrue(hasattr(self.page, 'empty_page'), 'folder drop targets the import page')
        mime = QtCore.QMimeData(); mime.setUrls([QtCore.QUrl.fromLocalFile(str(self.root))])
        enter = QtGui.QDragEnterEvent(QtCore.QPoint(50, 50), QtCore.Qt.CopyAction, mime, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        drop = QtGui.QDropEvent(QtCore.QPointF(50, 50), QtCore.Qt.CopyAction, mime, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        QtWidgets.QApplication.sendEvent(self.page.empty_page, enter)
        self.assertTrue(enter.isAccepted())
        QtWidgets.QApplication.sendEvent(self.page.empty_page, drop)
        self.wait(lambda: self.page.session is not None and not self.page.active_workers())
        self.assertEqual(self.page.grid.count(), 2)
        self.assertTrue(self.page.splitter.isVisible())

    def test_cancelled_initial_import_returns_to_enabled_import_entry(self):
        self.assertTrue(hasattr(self.page, 'empty_open_button'), 'empty state offers import')
        self.page.open_folder(str(self.root))
        self.assertTrue(self.page.cancel_button.isVisible())
        self.assertFalse(self.page.empty_open_button.isEnabled())
        self.page.cancel_button.click()
        self.wait(lambda: not self.page.active_workers())
        self.assertIsNone(self.page.session)
        self.assertTrue(self.page.empty_page.isVisible())
        self.assertTrue(self.page.empty_open_button.isEnabled())
        self.assertFalse(self.page.cancel_button.isVisible())
        self.load()
        self.assertTrue(self.page.splitter.isVisible())

    def test_failed_initial_import_keeps_import_available(self):
        self.assertTrue(hasattr(self.page, 'empty_page'), 'empty state offers retry')
        with patch.object(QtWidgets.QMessageBox, 'warning') as warning:
            self.page.open_folder(str(self.root / 'missing'))
            self.wait(lambda: not self.page.active_workers())
        warning.assert_called_once()
        self.assertTrue(self.page.empty_page.isVisible())
        self.assertTrue(self.page.empty_open_button.isEnabled())
        self.assertNotIn('正在', self.page.status.text())
        self.load()
        self.assertTrue(self.page.splitter.isVisible())

    def test_trash_collapses_when_empty_and_remains_available_after_removing_every_image(self):
        self.load()
        self.assertFalse(self.page.trash_list.isVisible())
        self.assertLess(self.page.trash_panel.height(), 60)
        self.page.grid.selectAll(); self.page.command_actions['remove'].trigger()
        self.wait(lambda: not self.page.active_workers())
        self.assertTrue(self.page.splitter.isVisible())
        self.assertFalse(self.page.empty_page.isVisible())
        self.assertTrue(self.page.trash_list.isVisible())
        self.assertEqual(self.page.position_label.text(), '0 / 0')
        self.page.trash_toggle.click()
        self.page._update_actions(); self.app.processEvents()
        self.assertFalse(self.page.trash_list.isVisible())
        self.assertEqual(self.page.trash_list.count(), 2)
        self.page.trash_toggle.click()
        self.page.trash_list.selectAll(); self.page.trash_restore_button.click()
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.grid.count(), 2)
        self.assertFalse(self.page.trash_list.isVisible())
        self.assertLess(self.page.trash_panel.height(), 60)

    def test_position_distinguishes_external_preview_and_cleared_preview(self):
        self.load()
        self.assertTrue(hasattr(self.page, 'position_label'), 'preview shows its position')
        external = Path(self.temp.name) / 'external.png'
        Image.new('RGB', (64, 48), 'green').save(external)
        self.page._drop_preview(self.page.preview, str(external), 'replace')
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.position_label.text(), '外部图片')
        self.page._return_preview(str(external))
        self.assertEqual(self.page.position_label.text(), '— / 2')

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
        self.page.command_actions['save'].trigger(); self.wait(lambda: not self.page._busy)
        project = self.page.session.project_root
        self.page.open_folder(str(project), project=True)
        self.wait(lambda: not self.page.active_workers() and not self.page._busy)
        strip = self.page.trash_list
        self.assertEqual(strip.count(), 1)
        image = strip.item(0).icon().pixmap(72, 54).toImage()
        self.assertEqual(image.pixelColor(image.rect().center()).name(), '#ff0000')
        with patch.object(self.page, '_confirm_purge', return_value=True):
            self.page.command_actions['save'].trigger(); self.wait(lambda: not self.page._busy)
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

    def test_import_creates_project_and_emits_ready_paths(self):
        self.load(); self.page.grid.setCurrentRow(1); self.page.command_actions['remove'].trigger()
        received = []; self.page.project_ready.connect(received.append)
        with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=self.temp.name):
            self.page._import()
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
        self.page._import(); self.app.processEvents()
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
        from yolo_backprop.data_screening.shortcuts import ShortcutSettings
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
        self.page.command_actions['save'].trigger()
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
            self.page.command_actions['save'].trigger(); self.wait(lambda: not self.page._busy)
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
            self.page.command_actions['save'].trigger(); self.wait(lambda: not self.page._busy)
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

    def test_both_single_preview_edges_open_comparison_in_drop_order_without_reloading_original(self):
        from yolo_backprop.data_screening.workers import PreviewWorker
        self.load()
        a, b = str(self.root / 'a.png'), str(self.root / 'b.png')
        for edge in ('left', 'right'):
            with self.subTest(edge=edge):
                self.page.exit_comparison(); self.page._show_primary(a)
                self.wait(lambda: not self.page.active_workers())
                view = self.page.preview
                view.scale(3.5, 3.5); view._fit = False
                self.app.processEvents()
                state = view.view_state()
                mime = self.page.grid.mimeData([self.page._rows[b]])
                positions = (QtCore.QPoint(10, 40), view.viewport().rect().center(),
                             QtCore.QPoint(view.viewport().width() - 10, 40))
                for index, (position, hint) in enumerate(zip(positions, ('compare_left', 'replace', 'compare'))):
                    event_type = QtGui.QDragEnterEvent if index == 0 else QtGui.QDragMoveEvent
                    event = event_type(position, QtCore.Qt.CopyAction, mime,
                                       QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
                    self.app.sendEvent(view.viewport(), event)
                    self.assertTrue(event.isAccepted())
                    self.assertEqual(view._drop_hint, hint)
                    self.assertEqual(view.displayed_path, a)
                    self.assertFalse(self.page._comparison_open)
                self.app.sendEvent(view.viewport(), QtGui.QDragLeaveEvent())
                with patch('yolo_backprop.data_screening.widget.PreviewWorker', wraps=PreviewWorker) as worker:
                    self.drop_image(view, b, positions[0 if edge == 'left' else 2], mime)
                    self.assertEqual([call.args[0] for call in worker.call_args_list], [b])
                left, right = self.page.preview, self.page.comparison_preview
                self.assertEqual((left.displayed_path, right.displayed_path),
                                 (b, a) if edge == 'left' else (a, b))
                original = right if edge == 'left' else left
                self.assertEqual(original.scene().items()[0].pixmap().cacheKey(), state[1].cacheKey())
                self.assertEqual(original.transform().m11(), state[2].m11())
                delta = original.mapToScene(original.viewport().rect().center()) - state[4]
                self.assertLess(abs(delta.x()) + abs(delta.y()), 2)
                self.assertIs(self.page._active_preview, left if edge == 'left' else right)
                self.assertTrue(self.page.comparison_panel.isVisible())

    def test_trash_drop_at_either_single_preview_edge_restores_then_compares(self):
        self.load()
        a, b = str(self.root / 'a.png'), str(self.root / 'b.png')
        for edge in ('left', 'right'):
            with self.subTest(edge=edge):
                self.page.restore_items(list(self.page.session.trash))
                self.page.exit_comparison(); self.page._show_primary(a)
                self.wait(lambda: not self.page.active_workers())
                self.transfer_mime(self.page.trash_panel, self.page.grid.mimeData([self.page._rows[b]]))
                mime = self.page.trash_list.mimeData([self.page._trash_rows[b]])
                position = QtCore.QPoint(10 if edge == 'left' else self.page.preview.viewport().width() - 10, 40)
                enter = QtGui.QDragEnterEvent(position, QtCore.Qt.CopyAction, mime,
                                             QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
                self.app.sendEvent(self.page.preview.viewport(), enter)
                self.assertTrue(enter.isAccepted())
                self.assertEqual(self.page.preview._drop_hint,
                                 'restore_compare_left' if edge == 'left' else 'restore_compare')
                self.drop_image(self.page.preview, b, position, mime)
                self.assertEqual((self.page.preview.displayed_path, self.page.comparison_preview.displayed_path),
                                 (b, a) if edge == 'left' else (a, b))
                self.assertEqual(self.page.grid.count(), 2)
                self.assertEqual(self.page.trash_list.count(), 0)
                self.assertTrue((self.original_root / 'b.png').exists())

    def test_left_edge_comparison_while_primary_load_is_pending_keeps_requested_images(self):
        self.load_many()
        b, c = str(self.root / 'b.png'), str(self.root / 'c.png')
        self.page._show_primary(c)
        self.assertTrue(self.page._preview_worker.wait(10000))
        # The old primary's ready signal is queued when its image moves to the right.
        self.drop_image(self.page.preview, b, QtCore.QPoint(10, 40))
        self.assertEqual(self.page.preview.displayed_path, b)
        self.assertEqual(self.page.comparison_preview.displayed_path, c)

    def test_dropping_single_preview_onto_either_own_edge_keeps_one_cached_image(self):
        self.load()
        view = self.page.preview
        key = view.scene().items()[0].pixmap().cacheKey()
        for x in (10, view.viewport().width() - 10):
            self.drop_image(view, self.root / 'a.png', QtCore.QPoint(x, 40), view.mime_data())
            self.assertFalse(self.page._comparison_open)
            self.assertEqual(view.scene().items()[0].pixmap().cacheKey(), key)
            self.assertNotIn('请选择另一张', self.page.status.text())

    def test_cancel_after_save_commit_suppresses_queued_purge_prompt_and_import(self):
        self.load(); self.page.command_actions['remove'].trigger()
        received = []; self.page.project_ready.connect(received.append)
        self.page._import()
        self.assertTrue(self.page._export_worker.wait(10000))
        self.page.stop_workers(); self.wait(lambda: not self.page._busy)
        self.page._confirm_purge.assert_not_called()
        self.assertEqual(received, [])

    def load_many(self):
        for name in ('c', 'd', 'e', 'f'):
            Image.new('RGB', (80, 60), 'green').save(self.root / (name + '.png'))
        self.load()

    def click_thumbnail(self, view, index, modifiers=QtCore.Qt.NoModifier):
        QtTest.QTest.mouseClick(view.viewport(), QtCore.Qt.LeftButton, modifiers,
                               view.visualItemRect(view.item(index)).center())
        self.app.processEvents()

    def transfer_mime(self, target, mime, accepted=True):
        position = QtCore.QPoint(12, 12)
        actions = QtCore.Qt.CopyAction
        enter = QtGui.QDragEnterEvent(position, actions, mime, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
        self.app.sendEvent(target, enter)
        self.assertEqual(enter.isAccepted(), accepted)
        if accepted:
            move = QtGui.QDragMoveEvent(position, actions, mime, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
            drop = QtGui.QDropEvent(QtCore.QPointF(position), actions, mime, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
            self.app.sendEvent(target, move)
            self.app.sendEvent(target, drop)
            self.assertTrue(drop.isAccepted())
            self.wait(lambda: not self.page.active_workers())

    def test_ctrl_and_shift_select_multiple_in_both_thumbnail_lists(self):
        self.load_many()
        for view in (self.page.grid, self.page.trash_list):
            if view is self.page.trash_list:
                self.page.grid.selectAll(); self.page.command_actions['remove'].trigger()
                self.app.processEvents()
            self.click_thumbnail(view, 0)
            self.click_thumbnail(view, 2, QtCore.Qt.ControlModifier)
            self.assertEqual({view.row(row) for row in view.selectedItems()}, {0, 2})
            self.click_thumbnail(view, 0, QtCore.Qt.ControlModifier)
            self.assertEqual({view.row(row) for row in view.selectedItems()}, {2})
            self.click_thumbnail(view, 0)
            self.click_thumbnail(view, 2, QtCore.Qt.ShiftModifier)
            self.assertEqual({view.row(row) for row in view.selectedItems()}, {0, 1, 2})

    def test_rubber_band_selects_multiple_in_both_thumbnail_lists(self):
        self.load()
        for view in (self.page.grid, self.page.trash_list):
            if view is self.page.trash_list:
                self.page.grid.selectAll(); self.page.command_actions['remove'].trigger()
                self.app.processEvents()
            view.clearSelection()
            first, second = [view.visualItemRect(view.item(i)) for i in range(2)]
            start = QtCore.QPoint(second.right() + 8, min(first.bottom() + 8, view.viewport().height() - 2))
            self.assertIsNone(view.itemAt(start), 'rubber band starts in empty space')
            end = first.topLeft() + QtCore.QPoint(2, 2)
            QtTest.QTest.mousePress(view.viewport(), QtCore.Qt.LeftButton, pos=start)
            move = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, QtCore.QPointF(end),
                                    QtCore.Qt.NoButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
            self.app.sendEvent(view.viewport(), move)
            QtTest.QTest.mouseRelease(view.viewport(), QtCore.Qt.LeftButton, pos=end)
            self.assertEqual(len(view.selectedItems()), 2)

    def test_drag_selected_batch_to_collapsed_trash_and_back_preserves_originals(self):
        self.load_many()
        originals = {p.name: p.read_bytes() for p in self.original_root.iterdir()}
        self.click_thumbnail(self.page.grid, 0)
        self.click_thumbnail(self.page.grid, 2, QtCore.Qt.ControlModifier)
        self.assertFalse(self.page.trash_list.isVisible())
        fixture = self
        def perform_drag(drag, *args):
            fixture.transfer_mime(fixture.page.trash_panel, drag.mimeData())
            return QtCore.Qt.CopyAction
        # Native drag loop is the platform boundary; payload and drop handlers are real.
        with patch.object(QtGui.QDrag, 'exec_', new=perform_drag):
            self.page.grid.startDrag(QtCore.Qt.CopyAction | QtCore.Qt.MoveAction)
        self.assertEqual([item.name for item in self.page.session.trash], ['a.png', 'c.png'])
        self.assertEqual(self.page.grid.count(), 4)
        self.assertTrue(self.page.trash_list.isVisible())
        self.page.trash_list.selectAll()
        mime = self.page.trash_list.mimeData(self.page.trash_list.selectedItems())
        self.transfer_mime(self.page.grid.viewport(), mime)
        self.assertEqual(self.page.grid.count(), 6)
        self.assertEqual(self.page.trash_list.count(), 0)
        self.assertEqual({p.name: p.read_bytes() for p in self.original_root.iterdir()}, originals)
        self.transfer_mime(self.page.grid.viewport(), mime, accepted=False)

    def test_drop_rejects_busy_external_and_stale_session_payloads(self):
        self.load()
        mime = self.page.grid.mimeData([self.page.grid.item(0)])
        self.page._set_busy(True)
        self.transfer_mime(self.page.trash_panel, mime, accepted=False)
        self.page._set_busy(False)
        external = QtCore.QMimeData()
        external.setUrls([QtCore.QUrl.fromLocalFile(str(self.root / 'a.png'))])
        self.transfer_mime(self.page.trash_panel, external, accepted=False)
        self.page.open_folder(str(self.page.session.project_root), project=True)
        self.wait(lambda: not self.page.active_workers())
        self.transfer_mime(self.page.trash_panel, mime, accepted=False)
        self.assertEqual(self.page.grid.count(), 2)
        self.assertEqual(self.page.trash_list.count(), 0)

    def test_drag_cancel_does_not_remove_selected_images(self):
        self.load(); self.page.grid.selectAll()
        with patch.object(QtGui.QDrag, 'exec_', return_value=QtCore.Qt.IgnoreAction) as drag:
            self.page.grid.startDrag(QtCore.Qt.CopyAction | QtCore.Qt.MoveAction)
        # A desktop file manager must never be offered permission to move project files.
        self.assertEqual(drag.call_args.args, (QtCore.Qt.CopyAction, QtCore.Qt.CopyAction))
        self.assertEqual(self.page.grid.count(), 2)
        self.assertEqual(len(self.page.grid.selectedItems()), 2)
        self.assertEqual(self.page.session.trash, [])

    def click_preview(self, view):
        self.page.activateWindow()
        QtTest.QTest.mouseClick(view.viewport(), QtCore.Qt.LeftButton, pos=view.viewport().rect().center())
        self.app.processEvents()

    def test_comparison_navigation_controls_only_clicked_side_and_tracks_position(self):
        self.load_many()
        a, b, c, d = [str(self.root / (name + '.png')) for name in 'abcd']
        self.page.compare_with(b); self.wait(lambda: not self.page.active_workers())
        self.click_preview(self.page.comparison_preview)
        QtTest.QTest.keyClick(self.page.comparison_preview, QtCore.Qt.Key_Right)
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.comparison_preview.displayed_path, c)
        self.assertEqual(self.page.preview.displayed_path, a)
        self.assertEqual(self.page.position_label.text(), '3 / 6')
        self.page.following_button.click(); self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.comparison_preview.displayed_path, d)
        self.assertEqual(self.page.preview.displayed_path, a)
        self.click_preview(self.page.preview)
        QtTest.QTest.keyClick(self.page.preview, QtCore.Qt.Key_Right)
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.preview.displayed_path, b)
        self.assertEqual(self.page.comparison_preview.displayed_path, d)
        self.assertEqual(self.page.position_label.text(), '2 / 6')

    def test_navigation_uses_displayed_path_skips_other_side_and_stops_at_edges(self):
        self.load_many()
        self.page._show_primary(str(self.root / 'c.png'))
        self.page.compare_with(str(self.root / 'd.png'))
        self.wait(lambda: not self.page.active_workers())
        self.click_preview(self.page.preview)
        QtTest.QTest.keyClick(self.page.preview, QtCore.Qt.Key_Right)
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.preview.displayed_path, str(self.root / 'e.png'))
        self.assertEqual(self.page.comparison_preview.displayed_path, str(self.root / 'd.png'))
        for _ in range(4): QtTest.QTest.keyClick(self.page.preview, QtCore.Qt.Key_Right)
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.preview.displayed_path, str(self.root / 'f.png'))

    def test_empty_and_external_comparison_can_navigate_without_changing_primary(self):
        self.load_many(); self.page.command_actions['compare'].trigger()
        self.click_preview(self.page.comparison_preview)
        QtTest.QTest.keyClick(self.page.comparison_preview, QtCore.Qt.Key_Right)
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.comparison_preview.displayed_path, str(self.root / 'b.png'))
        external = Path(self.temp.name) / 'external.png'; Image.new('RGB', (60, 40)).save(external)
        self.page.compare_with(str(external)); self.wait(lambda: not self.page.active_workers())
        self.click_preview(self.page.comparison_preview)
        self.assertEqual(self.page.position_label.text(), '外部图片')
        QtTest.QTest.keyClick(self.page.comparison_preview, QtCore.Qt.Key_Left)
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.comparison_preview.displayed_path, str(self.root / 'f.png'))
        self.assertEqual(self.page.preview.displayed_path, str(self.root / 'a.png'))

    def test_exit_comparison_has_no_button_but_escape_still_works(self):
        self.load(); self.page.compare_with(str(self.root / 'b.png'))
        self.wait(lambda: not self.page.active_workers())
        self.assertNotIn('退出对比', [b.text() for b in self.page.findChildren(QtWidgets.QAbstractButton)])
        self.click_preview(self.page.comparison_preview)
        QtTest.QTest.keyClick(self.page.comparison_preview, QtCore.Qt.Key_Escape)
        self.assertTrue(self.page.comparison_panel.isHidden())
        self.assertEqual(self.page.preview.displayed_path, str(self.root / 'a.png'))

    def test_restoring_unrelated_image_keeps_both_comparison_images(self):
        self.load_many()
        self.page.grid.setCurrentRow(5); self.page.command_actions['remove'].trigger()
        self.page.grid.setCurrentRow(0); self.page.compare_with(str(self.root / 'b.png'))
        self.wait(lambda: not self.page.active_workers())
        self.page.restore_items(list(self.page.session.trash))
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.preview.displayed_path, str(self.root / 'a.png'))
        self.assertEqual(self.page.comparison_preview.displayed_path, str(self.root / 'b.png'))

    def test_mouse_dragging_selected_thumbnails_transfers_entire_selection_both_ways(self):
        self.load()
        for source, target in ((self.page.grid, self.page.trash_panel),
                               (self.page.trash_list, self.page.grid.viewport())):
            self.app.processEvents(); source.selectAll()
            position = source.visualItemRect(source.item(0)).center()
            calls = []
            fixture = self
            def native_drag(drag, *args):
                calls.append(True)
                fixture.transfer_mime(target, drag.mimeData())
                return QtCore.Qt.CopyAction
            with patch.object(QtGui.QDrag, 'exec_', new=native_drag):
                QtTest.QTest.mousePress(source.viewport(), QtCore.Qt.LeftButton, pos=position)
                for distance in (1, 30, 50):
                    event = QtGui.QMouseEvent(QtCore.QEvent.MouseMove,
                            QtCore.QPointF(position + QtCore.QPoint(distance, 0)), QtCore.Qt.NoButton,
                            QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
                    self.app.sendEvent(source.viewport(), event)
                QtTest.QTest.mouseRelease(source.viewport(), QtCore.Qt.LeftButton, pos=position)
            self.assertEqual(len(calls), 1, 'a real mouse drag must start one native drag loop')
            self.assertEqual(source.count(), 0)
        self.assertEqual(self.page.grid.count(), 2)

    def test_invalid_and_same_area_item_transfers_are_ignored(self):
        import json
        from yolo_backprop.data_screening.views import ITEMS_MIME
        self.load()
        mime = self.page.grid.mimeData([self.page.grid.item(0)])
        self.transfer_mime(self.page.grid.viewport(), mime, accepted=False)
        payload = json.loads(bytes(mime.data(ITEMS_MIME)))
        payload['ids'] *= 2
        mime.setData(ITEMS_MIME, json.dumps(payload).encode())
        self.transfer_mime(self.page.trash_panel, mime, accepted=False)
        for bad in (b'{bad', b'[]', b'{"session": "x", "source": "images", "ids": [null]}'):
            mime.setData(ITEMS_MIME, bad)
            self.transfer_mime(self.page.trash_panel, mime, accepted=False)
        self.assertEqual(self.page.grid.count(), 2)

    def test_removing_primary_during_comparison_keeps_other_side_then_promotes_last_image(self):
        self.load_many()
        b = str(self.root / 'b.png')
        self.page.compare_with(b); self.wait(lambda: not self.page.active_workers())
        mime = self.page.grid.mimeData([self.page.grid.item(0)])
        self.transfer_mime(self.page.trash_panel, mime)
        self.assertTrue(self.page.comparison_panel.isVisible())
        self.assertEqual(self.page.comparison_preview.displayed_path, b)
        self.assertNotEqual(self.page.preview.displayed_path, b)
        remaining = [self.page.grid.item(i) for i in range(self.page.grid.count())
                     if str(self.page.grid.item(i).data(QtCore.Qt.UserRole).source) != b]
        self.transfer_mime(self.page.trash_list.viewport(), self.page.grid.mimeData(remaining))
        self.assertTrue(self.page.comparison_panel.isHidden())
        self.assertEqual(self.page.preview.displayed_path, b)

    def test_custom_navigation_binding_and_rapid_right_side_changes_keep_latest_image(self):
        self.load_many(); self.page.compare_with(str(self.root / 'b.png'))
        self.wait(lambda: not self.page.active_workers())
        self.page.update_shortcuts({'next': 'N'})
        self.click_preview(self.page.comparison_preview)
        for _ in range(4): QtTest.QTest.keyClick(self.page.comparison_preview, QtCore.Qt.Key_N)
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.comparison_preview.displayed_path, str(self.root / 'f.png'))
        self.assertEqual(self.page.preview.displayed_path, str(self.root / 'a.png'))

    def test_dragging_comparison_images_swaps_both_directions_and_preserves_view_state(self):
        self.load(); self.page.compare_with(str(self.root / 'b.png'))
        self.wait(lambda: not self.page.active_workers())
        left, right = self.page.preview, self.page.comparison_preview
        left.scale(3.5, 3.5); left._fit = False
        left.horizontalScrollBar().setValue(30)
        right.scale(1.5, 1.5); right._fit = False
        right.verticalScrollBar().setValue(60)
        self.app.processEvents()  # Let Qt lay out the scrollbars created by zooming.
        scales = (left.transform().m11(), right.transform().m11())
        centers = [view.mapToScene(view.viewport().rect().center()) for view in (left, right)]
        pixels = [view.scene().items()[0].pixmap().cacheKey() for view in (left, right)]
        with patch('yolo_backprop.data_screening.widget.PreviewWorker', wraps=__import__(
                'yolo_backprop.data_screening.workers', fromlist=['PreviewWorker']).PreviewWorker) as worker:
            self.drop_image(right, self.root / 'a.png', mime=left.mime_data())
            self.assertEqual((left.displayed_path, right.displayed_path),
                             (str(self.root / 'b.png'), str(self.root / 'a.png')))
            self.assertTrue(self.page.comparison_panel.isVisible())
            self.assertEqual((left.transform().m11(), right.transform().m11()), scales[::-1])
            self.assertEqual([view.scene().items()[0].pixmap().cacheKey() for view in (left, right)], pixels[::-1])
            for view, center in zip((left, right), centers[::-1]):
                delta = view.mapToScene(view.viewport().rect().center()) - center
                self.assertLess(abs(delta.x()) + abs(delta.y()), 2)
            self.drop_image(left, self.root / 'a.png', mime=right.mime_data())
            self.assertEqual((left.displayed_path, right.displayed_path),
                             (str(self.root / 'a.png'), str(self.root / 'b.png')))
            worker.assert_not_called()
        self.assertEqual(self.page.grid.count(), 2)
        self.assertEqual(self.page.trash_list.count(), 0)

    def test_preview_drop_on_itself_does_not_exit_or_reload_comparison(self):
        self.load(); self.page.compare_with(str(self.root / 'b.png'))
        self.wait(lambda: not self.page.active_workers())
        for view in (self.page.preview, self.page.comparison_preview):
            path = view.displayed_path
            key = view.scene().items()[0].pixmap().cacheKey()
            self.drop_image(view, path, mime=view.mime_data())
            self.assertEqual(view.displayed_path, path)
            self.assertEqual(view.scene().items()[0].pixmap().cacheKey(), key)
        self.assertTrue(self.page.comparison_panel.isVisible())
        self.assertNotIn('请选择另一张', self.page.status.text())

    def test_preview_can_move_to_trash_and_trash_drop_restores_into_target_side(self):
        self.load_many()
        a, b = str(self.root / 'a.png'), str(self.root / 'b.png')
        self.page.compare_with(b); self.wait(lambda: not self.page.active_workers())
        self.transfer_mime(self.page.trash_panel, self.page.comparison_preview.mime_data())
        self.assertEqual([item.name for item in self.page.session.trash], ['b.png'])
        self.assertEqual(self.page.preview.displayed_path, a)
        self.page.command_actions['compare'].trigger()
        mime = self.page.trash_list.mimeData([self.page.trash_list.item(0)])
        self.drop_image(self.page.comparison_preview, b, mime=mime)
        self.assertEqual(self.page.preview.displayed_path, a)
        self.assertEqual(self.page.comparison_preview.displayed_path, b)
        self.assertEqual(self.page.trash_list.count(), 0)
        self.assertEqual(self.page.grid.count(), 6)
        self.assertTrue((self.original_root / 'b.png').exists())

    def test_external_or_stale_preview_cannot_be_moved_into_project_trash(self):
        self.load()
        external = Path(self.temp.name) / 'external.png'; Image.new('RGB', (60, 40)).save(external)
        self.page._drop_preview(self.page.preview, str(external), 'replace')
        self.wait(lambda: not self.page.active_workers())
        self.transfer_mime(self.page.trash_panel, self.page.preview.mime_data(), accepted=False)
        self.page._show_primary(str(self.root / 'a.png')); self.wait(lambda: not self.page.active_workers())
        old = self.page.preview.mime_data()
        self.page.open_folder(str(self.page.session.project_root), project=True)
        self.wait(lambda: not self.page.active_workers())
        self.transfer_mime(self.page.trash_panel, old, accepted=False)
        self.assertEqual(self.page.trash_list.count(), 0)

    def test_swap_during_pending_comparison_ignores_queued_result(self):
        self.load_many(); self.page.compare_with(str(self.root / 'b.png'))
        self.wait(lambda: not self.page.active_workers())
        self.page.compare_with(str(self.root / 'c.png'))
        self.assertTrue(self.page._comparison_worker.wait(10000))
        # The c.png ready event is queued; dropping a.png must still swap requested slots.
        self.page._drop_preview(self.page.comparison_preview, str(self.root / 'a.png'), 'replace')
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.preview.displayed_path, str(self.root / 'c.png'))
        self.assertEqual(self.page.comparison_preview.displayed_path, str(self.root / 'a.png'))

    def test_thumbnail_press_waits_for_click_release_and_cancelled_drag_keeps_preview(self):
        self.load()
        view = self.page.grid
        start = view.visualItemRect(view.item(1)).center()
        QtTest.QTest.mousePress(view.viewport(), QtCore.Qt.LeftButton, pos=start)
        self.assertEqual(self.page._preview_requested, str(self.root / 'a.png'))
        with patch.object(QtGui.QDrag, 'exec_', return_value=QtCore.Qt.IgnoreAction):
            for distance in (1, 30, 50):
                event = QtGui.QMouseEvent(QtCore.QEvent.MouseMove,
                        QtCore.QPointF(start + QtCore.QPoint(distance, 0)), QtCore.Qt.NoButton,
                        QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
                self.app.sendEvent(view.viewport(), event)
        QtTest.QTest.mouseRelease(view.viewport(), QtCore.Qt.LeftButton, pos=start)
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.preview.displayed_path, str(self.root / 'a.png'))
        self.click_thumbnail(view, 1); self.wait(lambda: not self.page.active_workers())
        self.assertEqual(self.page.preview.displayed_path, str(self.root / 'b.png'))

    def test_dropping_primary_into_empty_comparison_is_a_quiet_noop(self):
        self.load(); self.page.command_actions['compare'].trigger()
        self.drop_image(self.page.comparison_preview, self.root / 'a.png', mime=self.page.preview.mime_data())
        self.assertEqual(self.page.preview.displayed_path, str(self.root / 'a.png'))
        self.assertIsNone(self.page.comparison_preview.displayed_path)
        self.assertNotIn('请选择另一张', self.page.status.text())

    def test_native_preview_drag_swaps_then_keyboard_controls_the_drop_target(self):
        self.load_many(); self.page.compare_with(str(self.root / 'b.png'))
        self.wait(lambda: not self.page.active_workers())
        source, target = self.page.preview, self.page.comparison_preview
        position = source.viewport().rect().center()
        calls = []
        fixture = self
        def native_drag(drag, *args):
            calls.append(True)
            fixture.drop_image(target, fixture.root / 'a.png', mime=drag.mimeData())
            return QtCore.Qt.CopyAction
        self.page.activateWindow()
        with patch.object(QtGui.QDrag, 'exec_', new=native_drag):
            QtTest.QTest.mousePress(source.viewport(), QtCore.Qt.LeftButton, pos=position)
            move = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, QtCore.QPointF(position + QtCore.QPoint(40, 0)),
                                    QtCore.Qt.NoButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
            self.app.sendEvent(source.viewport(), move)
            QtTest.QTest.mouseRelease(source.viewport(), QtCore.Qt.LeftButton, pos=position)
        self.assertEqual(len(calls), 1)
        self.assertIs(self.page._active_preview, target)
        QtTest.QTest.keyClick(target, QtCore.Qt.Key_Right)
        self.wait(lambda: not self.page.active_workers())
        self.assertEqual(target.displayed_path, str(self.root / 'c.png'))
        self.assertEqual(source.displayed_path, str(self.root / 'b.png'))
