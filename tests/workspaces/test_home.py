import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt5 import QtCore, QtTest, QtWidgets


class HomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        from yolo_backprop.workspaces.store import WorkspaceStore
        from yolo_backprop.workspaces.home import WorkspaceHome
        self.store = WorkspaceStore(self.root / 'config' / 'workspaces.json')
        self.home = WorkspaceHome(self.store)
        self.addCleanup(self.home.close)
        self.home.resize(1180, 760); self.home.show(); self.app.processEvents()

    def test_empty_home_offers_new_workspace_without_creating_a_default_folder(self):
        self.assertEqual(self.home.cards, [])
        self.assertTrue(self.home.create_button.isVisible())
        self.assertTrue(self.home.open_button.isVisible())
        self.assertTrue(self.home.empty_label.isVisible())
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertTrue(all(card.isVisible() for card in self.home.cards))

    def test_open_existing_card_only_requests_existing_project_without_writing_it(self):
        from yolo_backprop.workspaces.store import MARKER, WorkspaceStore
        other = WorkspaceStore(self.root / 'other-config' / 'workspaces.json')
        root = other.create(self.root, '保存的项目')
        other.update(root, state={'training': {'epochs': 37}})
        marker = (root / MARKER).read_bytes()
        received = []; self.home.workspace_requested.connect(received.append)
        self.home.location_ready.connect(lambda info: received.append(info['root']))
        with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=str(root)):
            QtTest.QTest.mouseClick(self.home.open_button, QtCore.Qt.LeftButton)
        self.assertEqual(received, [str(root)])
        self.assertEqual((root / MARKER).read_bytes(), marker)
        self.assertFalse(self.store.path.exists(), 'registration must wait for workbench switching guards')

    def test_cancel_open_existing_project_does_not_create_files_or_request_open(self):
        received = []; self.home.workspace_requested.connect(received.append)
        self.home.location_ready.connect(lambda info: received.append(info['root']))
        with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=''):
            QtTest.QTest.mouseClick(self.home.open_button, QtCore.Qt.LeftButton)
        self.assertEqual(received, [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_open_card_accepts_a_readable_image_folder_without_creating_a_project_in_it(self):
        from PIL import Image
        source = self.root / '没有结构的图片'; source.mkdir()
        image = source / 'photo.png'; Image.new('RGB', (80, 60), 'red').save(image)
        before = image.read_bytes(); received = []
        self.home.workspace_requested.connect(received.append)
        self.home.location_ready.connect(lambda info: received.append(info['root']))
        with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=str(source)):
            QtTest.QTest.mouseClick(self.home.open_button, QtCore.Qt.LeftButton)
        self.assertEqual(received, [str(source)])
        self.assertEqual(list(source.iterdir()), [image]); self.assertEqual(image.read_bytes(), before)
        self.assertFalse(self.store.path.exists())

    def test_open_rejects_ordinary_and_corrupt_folders_without_initializing_them(self):
        from yolo_backprop.workspaces.store import MARKER
        plain = self.root / '普通文件夹'; plain.mkdir()
        original = plain / '用户文件.txt'; original.write_text('keep')
        lookalike = self.root / '含projects的普通目录'; (lookalike / 'projects').mkdir(parents=True)
        broken = self.root / '损坏项目'; broken.mkdir(); (broken / MARKER).write_text('{broken')
        received = []; self.home.workspace_requested.connect(received.append)
        self.home.location_ready.connect(lambda info: received.append(info['root']))
        for root in (plain, lookalike, broken):
            with self.subTest(root=root.name), \
                 patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=str(root)), \
                 patch.object(QtWidgets.QMessageBox, 'warning'):
                QtTest.QTest.mouseClick(self.home.open_button, QtCore.Qt.LeftButton)
        self.assertEqual(received, [])
        self.assertFalse(self.store.path.exists())
        self.assertEqual([p.name for p in plain.iterdir()], ['用户文件.txt'])
        self.assertEqual(original.read_text(), 'keep')
        self.assertEqual([p.name for p in lookalike.iterdir()], ['projects'])
        self.assertEqual((broken / MARKER).read_text(), '{broken')

    def test_combined_name_and_location_creates_matching_folder_and_opens_project(self):
        received = []
        self.home.workspace_requested.connect(received.append)
        self.home.location_ready.connect(lambda info: received.append(info['root']))
        def name_project():
            dialog = self.app.activeModalWidget()
            if dialog:
                dialog.location_edit.setText(str(self.root))
                dialog.name_edit.setText('测试空间'); dialog.create_button.click()
        timer = QtCore.QTimer(); timer.setSingleShot(True)
        timer.timeout.connect(name_project); timer.start(0)
        try:
            with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=str(self.root)):
                QtTest.QTest.mouseClick(self.home.create_button, QtCore.Qt.LeftButton)
        finally: timer.stop()
        location = self.root / '测试空间'
        self.assertEqual(received, [str(location)])
        self.assertTrue((location / 'projects').is_dir())

    def test_cancel_project_name_leaves_no_folder_or_history(self):
        timer = QtCore.QTimer(); timer.setSingleShot(True)
        timer.timeout.connect(lambda: self.app.activeModalWidget().reject() if self.app.activeModalWidget() else None)
        timer.start(0)
        try:
            with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=str(self.root)):
                self.home.create_workspace()
        finally: timer.stop()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_card_context_actions_open_copy_and_request_delete(self):
        root = self.store.create(self.root, '右键项目'); self.home.refresh()
        opened, deleted = [], []
        self.home.workspace_requested.connect(opened.append)
        self.home.delete_requested.connect(deleted.append)
        menu = self.home.create_context_menu(str(root)); self.addCleanup(menu.close)
        actions = {action.objectName(): action for action in menu.actions() if not action.isSeparator()}
        actions['copy_path'].trigger()
        self.assertEqual(self.app.clipboard().text(), str(root))
        actions['open'].trigger(); actions['delete'].trigger()
        self.assertEqual(opened, [str(root)]); self.assertEqual(deleted, [str(root)])

    def test_refresh_drops_a_project_deleted_outside_the_app(self):
        import shutil
        root = self.store.create(self.root, '外部删除'); self.home.refresh()
        self.assertEqual(len(self.home.cards), 1)
        shutil.rmtree(root); self.home.refresh()
        self.assertEqual(len(self.home.cards), 0)

    def test_refresh_immediately_hides_retired_cards_without_waiting_for_deferred_deletion(self):
        root = self.store.create(self.root, '旧卡片')
        self.home.refresh(); self.app.processEvents()
        card = next(card for card in self.home.cards if card.info)
        self.assertTrue(card.isVisible())
        self.store.forget(root); self.home.refresh()
        self.assertFalse(card.isVisible())
        self.assertEqual(len(self.home.cards), 0)

    def test_cancel_location_selection_keeps_current_location_without_creating_files(self):
        from yolo_backprop.workspaces.home import CreateProjectDialog
        dialog = CreateProjectDialog(self.root); self.addCleanup(dialog.close)
        with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=''):
            dialog.browse_button.click()
        self.assertEqual(dialog.location_edit.text(), str(self.root))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_location_change_revalidates_destination_and_success_remembers_parent(self):
        from yolo_backprop.workspaces.home import CreateProjectDialog
        other = self.root / '另一个位置'; other.mkdir()
        (other / '已有项目').mkdir()
        dialog = CreateProjectDialog(self.root); self.addCleanup(dialog.close)
        dialog.name_edit.setText('已有项目')
        self.assertTrue(dialog.create_button.isEnabled())
        dialog.location_edit.setText(str(other))
        self.assertFalse(dialog.create_button.isEnabled())
        dialog.location_edit.setText(str(other / '不存在'))
        self.assertFalse(dialog.create_button.isEnabled())
        dialog.location_edit.setText(str(other)); dialog.name_edit.setText('新的项目')
        self.assertTrue(dialog.create_button.isEnabled())
        self.assertIn(str(other / '新的项目'), dialog.destination.text())
        self.store.remember_creation_location(other)
        self.assertEqual(type(self.store)(self.store.path).creation_location(), other)

    def test_recent_cards_distinguish_same_named_projects_by_visible_path_and_time(self):
        other = self.root / 'other'; other.mkdir()
        first = self.store.create(self.root, '同名项目')
        second = self.store.create(other, '同名项目')
        self.home.refresh()
        self.assertEqual(len(self.home.cards), 2)
        self.assertNotEqual(self.home.cards[0].path_text, self.home.cards[1].path_text)
        for card in self.home.cards:
            self.assertIn('最近打开', card.time_text)
            self.assertIn(card.info['root'], card.accessibleDescription())

    def test_default_name_is_offered_but_invalid_and_existing_custom_names_cannot_be_submitted(self):
        from yolo_backprop.workspaces.home import CreateProjectDialog
        (self.root / '已有项目').mkdir()
        dialog = CreateProjectDialog(self.root); self.addCleanup(dialog.close)
        dialog.show(); self.app.processEvents()
        self.assertEqual(dialog.name_edit.text(), '新项目')
        self.assertTrue(dialog.create_button.isEnabled())
        for name in ('../桌面', 'a/b', 'a\\b', '已有项目', 'CON', '末尾.'):
            with self.subTest(name=name):
                dialog.name_edit.setText(name)
                self.assertFalse(dialog.create_button.isEnabled())
                dialog.accept()  # A Return key or programmatic accept must not bypass validation.
                self.assertTrue(dialog.isVisible())
                self.assertNotEqual(dialog.result(), dialog.Accepted)
        dialog.name_edit.setText('零件检测')
        self.assertTrue(dialog.create_button.isEnabled())
        self.assertIn(str(self.root / '零件检测'), dialog.destination.text())
        dialog.create_button.click()
        self.assertEqual(dialog.result(), dialog.Accepted)
        self.assertEqual([p.name for p in self.root.iterdir()], ['已有项目'])

    def test_return_accepts_default_custom_and_blank_fallback_names_without_creating_files(self):
        from yolo_backprop.workspaces.home import CreateProjectDialog
        cases = ((QtCore.Qt.Key_Return, None, '新项目'),
                 (QtCore.Qt.Key_Enter, '零件检测', '零件检测'),
                 (QtCore.Qt.Key_Return, '', '新项目'),
                 (QtCore.Qt.Key_Enter, '   ', '新项目'))
        for key, entered, expected in cases:
            with self.subTest(key=key, entered=entered):
                dialog = CreateProjectDialog(self.root); self.addCleanup(dialog.close)
                dialog.show(); self.app.processEvents()
                if entered is not None: dialog.name_edit.setText(entered)
                dialog.name_edit.setFocus()
                QtTest.QTest.keyClick(dialog.name_edit, key)
                self.assertEqual(dialog.result(), dialog.Accepted)
                self.assertEqual(dialog.name_edit.text(), expected)
                self.assertIn(str(self.root / expected), dialog.destination.text())
                self.assertEqual(list(self.root.iterdir()), [])

    def test_default_name_skips_existing_directory_file_and_dangling_link(self):
        from yolo_backprop.workspaces.home import CreateProjectDialog
        (self.root / '新项目').mkdir()
        original = self.root / '新项目 2'; original.write_text('keep')
        (self.root / '新项目 3').symlink_to(self.root / '不存在的目标')
        dialog = CreateProjectDialog(self.root); self.addCleanup(dialog.close)
        dialog.show(); self.app.processEvents()
        self.assertEqual(dialog.name_edit.text(), '新项目 4')
        dialog.name_edit.clear()
        self.assertTrue(dialog.create_button.isEnabled())
        self.assertIn(str(self.root / '新项目 4'), dialog.destination.text())
        QtTest.QTest.keyClick(dialog.name_edit, QtCore.Qt.Key_Return)
        self.assertEqual(dialog.result(), dialog.Accepted)
        self.assertEqual(dialog.name_edit.text(), '新项目 4')
        self.assertEqual(original.read_text(), 'keep')
        self.assertFalse((self.root / '新项目 4').exists())

    def test_return_in_styled_home_dialog_accepts_once_instead_of_cancelling(self):
        from yolo_backprop.workspaces.home import CreateProjectDialog
        for key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            with self.subTest(key=key):
                dialog = CreateProjectDialog(self.root, self.home); self.addCleanup(dialog.close)
                accepted = QtTest.QSignalSpy(dialog.accepted)
                rejected = QtTest.QSignalSpy(dialog.rejected)
                dialog.show(); dialog.activateWindow(); self.app.processEvents()
                QtTest.QTest.qWaitForWindowActive(dialog, 1000)
                dialog.name_edit.setFocus()
                self.assertTrue(dialog.create_button.isDefault())
                QtTest.QTest.keyClick(dialog.name_edit, key)
                self.assertEqual(dialog.result(), dialog.Accepted)
                self.assertEqual(len(accepted), 1)
                self.assertEqual(len(rejected), 0)

    def test_project_cards_keep_dimensions_through_resize_and_refresh(self):
        for name in ('项目一', '项目二', '项目三', '项目四', '项目五', '项目六'):
            self.store.create(self.root, name)
        self.home.refresh()
        for width in (1600, 800, 1180, 1600):
            self.home.resize(width, 760); self.app.processEvents(); self.app.processEvents()
            expected = self.home.cards[0].sizeHint()
            for card in self.home.cards:
                self.assertEqual(card.size(), expected)
                self.assertLessEqual(card.geometry().right(), self.home.scroll.viewport().width())
        for row in self.store.recent()[2:]: self.store.forget(row['root'])
        self.home.refresh(); self.app.processEvents(); self.app.processEvents()
        for card in self.home.cards:
            self.assertEqual(card.size(), self.home.cards[0].sizeHint())

    def test_clicking_workspace_card_requests_that_workspace_and_grid_adapts(self):
        root = self.store.create(self.root, '现有空间'); self.home.refresh(); self.app.processEvents()
        received = []; self.home.workspace_requested.connect(received.append)
        self.home.location_ready.connect(lambda info: received.append(info['root']))
        card = next(c for c in self.home.cards if c.info)
        QtTest.QTest.mouseClick(card, QtCore.Qt.LeftButton)
        self.assertEqual(received, [str(root)])
        self.home.resize(800, 620); self.app.processEvents()
        for item in self.home.cards:
            self.assertGreaterEqual(item.width(), 240)
            self.assertLessEqual(item.geometry().right(), self.home.scroll.viewport().width())

    def test_invalid_recent_timestamp_does_not_prevent_opening_home(self):
        root = self.store.create(self.root, '旧项目')
        for value in ('invalid', 1e100, None):
            with self.subTest(value=value):
                self.store.update(root, last_opened=value)
                self.home.refresh()
                self.assertEqual(len(self.home.cards), 1)
                self.assertIn('未知', self.home.cards[0].time_text)
