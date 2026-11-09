import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
import shutil
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from PyQt5 import QtCore, QtTest, QtWidgets


class WorkspaceIntegrationTests(unittest.TestCase):
    def setUp(self):
        from tests.model_development.test_integration import IntegrationTests
        IntegrationTests.setUpClass()
        self.fixture = IntegrationTests(); self.fixture.start_home = True
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.app = self.fixture.app; self.window = self.fixture.window
        self.controller = self.fixture.controller()
        self.home = self.controller.workspace_home
        self.root = Path(self.fixture.temp.name)

    def test_software_starts_on_home_with_annotation_shortcuts_suspended(self):
        self.assertIs(self.controller.stack.currentWidget(), self.home.home)
        self.assertFalse(self.controller.navigation.isVisible())
        self.assertFalse(self.window.menubar.isVisible())
        self.assertTrue(self.window.actionPolygon.shortcut().isEmpty())
        self.assertIsNone(self.home.current_root)

    def test_create_from_home_enters_workspace_and_same_card_keeps_live_forms(self):
        root = self.root / '测试空间'
        def name_project():
            dialog = self.app.activeModalWidget()
            if dialog:
                dialog.location_edit.setText(str(self.root))
                dialog.name_edit.setText('测试空间'); dialog.create_button.click()
        timer = QtCore.QTimer(); timer.setSingleShot(True)
        timer.timeout.connect(name_project); timer.start(0)
        try:
            with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=str(self.root)):
                QtTest.QTest.mouseClick(self.home.home.create_button, QtCore.Qt.LeftButton)
        finally: timer.stop()
        self.app.processEvents()
        c = self.controller
        self.assertEqual(self.home.current_root, root)
        self.assertEqual(c.screening_widget.workspace.root, root)
        self.assertTrue(c.navigation.isVisible())
        self.assertIs(c.stack.currentWidget(), c.screening_widget)
        self.assertFalse(self.home.home.isVisible())
        for action in (c.screening_action, c.annotation_action, c.development_action):
            self.assertTrue(c.navigation.widgetForAction(action).isVisible())
        c.show_development(); self.app.processEvents()
        panel = c.widget; panel.train_tab.tr_epochs.setValue(23)
        c.home_action.trigger(); self.app.processEvents()
        self.assertIs(c.stack.currentWidget(), self.home.home)
        self.assertTrue(self.home.open_workspace(root)); self.app.processEvents()
        self.assertIs(c.widget, panel)
        self.assertEqual(c.widget.train_tab.tr_epochs.value(), 23)
        self.assertEqual(c.widget.train_tab.tr_results.currentText(), str(root / 'results'))

    def test_return_creates_and_enters_default_project_and_blank_next_name_is_unique(self):
        from yolo_backprop.workspaces.store import MARKER
        from PyQt5.QtCore import QTimer
        for clear, key, expected in ((False, QtCore.Qt.Key_Return, '新项目'),
                                     (True, QtCore.Qt.Key_Enter, '新项目 2')):
            with self.subTest(clear=clear):
                self.home.show_home()
                def submit():
                    dialog = self.app.activeModalWidget()
                    if dialog:
                        dialog.location_edit.setText(str(self.root))
                        if clear: dialog.name_edit.clear()
                        QtTest.QTest.keyClick(dialog.name_edit, key)
                        if dialog.isVisible(): dialog.reject()  # Old disabled-default behavior must fail without hanging.
                timer = QTimer(); timer.setSingleShot(True); timer.timeout.connect(submit); timer.start(0)
                try:
                    with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=str(self.root)):
                        QtTest.QTest.mouseClick(self.home.home.create_button, QtCore.Qt.LeftButton)
                finally: timer.stop()
                root = self.root / expected
                self.assertEqual(self.home.current_root, root)
                self.assertTrue((root / MARKER).is_file())
                self.assertEqual(self.home.store.read(root)['name'], expected)
                self.assertEqual(self.controller.screening_widget.workspace.root, root)
                self.assertIs(self.controller.stack.currentWidget(), self.controller.screening_widget)
                self.assertTrue(self.controller.navigation.isVisible())
        self.assertTrue((self.root / '新项目' / MARKER).is_file())
        self.assertFalse((self.root / MARKER).exists())

    def test_delete_current_project_moves_folder_and_does_not_recreate_it_on_exit(self):
        root = self.home.store.create(self.root, '待删除项目')
        self.home.open_workspace(root); self.home.show_home()
        recycle = self.root / 'recycle'; recycle.mkdir()
        def move_to_trash(source):
            destination = recycle / Path(source).name
            shutil.move(source, destination)
            return True, str(destination)
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.Yes), \
             patch.object(QtCore.QFile, 'moveToTrash', move_to_trash):
            self.assertTrue(self.home.delete_workspace(str(root)))
        self.assertFalse(root.exists())
        self.assertTrue((recycle / root.name).is_dir())
        self.assertIsNone(self.home.current_root)
        self.assertNotIn(str(root), [row['root'] for row in self.home.store.recent()])
        self.assertTrue(self.window.close()); self.assertFalse(root.exists())

    def test_select_existing_project_restores_training_and_registers_once(self):
        from yolo_backprop.workspaces.store import WorkspaceStore
        other = WorkspaceStore(self.root / 'other-config' / 'workspaces.json')
        root = other.create(self.root, '已有训练项目')
        other.update(root, state={'page': 'development', 'training': {'epochs': 37}})
        ownership = other.read(root)['ownership']
        original = root / '原数据.txt'; original.write_text('keep')
        self.assertTrue(self.home.home.open_button.isVisible())
        with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=str(root)):
            QtTest.QTest.mouseClick(self.home.home.open_button, QtCore.Qt.LeftButton)
        c = self.controller
        self.assertEqual(self.home.current_root, root)
        self.assertIs(c.stack.currentWidget(), c.widget)
        self.assertEqual(c.widget.train_tab.tr_epochs.value(), 37)
        c.widget.train_tab.tr_epochs.setValue(55)
        self.home.show_home()
        with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=str(root)):
            QtTest.QTest.mouseClick(self.home.home.open_button, QtCore.Qt.LeftButton)
        self.assertEqual(c.widget.train_tab.tr_epochs.value(), 55)
        self.assertEqual([row['root'] for row in self.home.store.recent()].count(str(root)), 1)
        self.assertEqual(self.home.store.read(root)['ownership'], ownership)
        self.assertEqual(original.read_text(), 'keep')

    def test_select_copied_project_can_open_but_does_not_gain_delete_permission(self):
        from yolo_backprop.workspaces.store import WorkspaceStore
        other = WorkspaceStore(self.root / 'other-config' / 'workspaces.json')
        original = other.create(self.root, '原始项目')
        copy = self.root / '复制的项目'; shutil.copytree(original, copy)
        self.assertTrue(self.home.home.open_button.isVisible())
        with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=str(copy)):
            QtTest.QTest.mouseClick(self.home.home.open_button, QtCore.Qt.LeftButton)
        self.assertEqual(self.home.current_root, copy)
        self.assertIs(self.controller.stack.currentWidget(), self.controller.screening_widget)
        with self.assertRaises(ValueError): self.home.store.validate_deletion(copy)
        self.assertTrue(original.is_dir()); self.assertTrue(copy.is_dir())

    def test_select_existing_project_during_task_does_not_register_or_switch(self):
        from yolo_backprop.workspaces.store import MARKER, WorkspaceStore
        class Worker(QtCore.QThread):
            def run(self):
                while not self.isInterruptionRequested(): self.msleep(5)
        current = self.home.store.create(self.root, '当前项目')
        other = WorkspaceStore(self.root / 'other-config' / 'workspaces.json')
        requested = other.create(self.root, '尚未登记项目')
        marker = (requested / MARKER).read_bytes()
        self.home.open_workspace(current); self.home.show_home()
        page = self.controller.screening_widget
        worker = Worker(); worker.start(); page._scan_worker = worker
        try:
            self.assertTrue(self.home.home.open_button.isVisible())
            with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=str(requested)), \
                 patch.object(QtWidgets.QMessageBox, 'warning'):
                QtTest.QTest.mouseClick(self.home.home.open_button, QtCore.Qt.LeftButton)
            self.assertEqual(self.home.current_root, current)
            self.assertNotIn(str(requested), [row['root'] for row in self.home.store.recent()])
            self.assertEqual((requested / MARKER).read_bytes(), marker)
            self.assertTrue(worker.isRunning())
        finally:
            worker.requestInterruption(); worker.wait(5000); page._scan_worker = None

    def test_image_folder_opens_using_private_copies_without_changing_source(self):
        source = self.root / '只有图片'; source.mkdir()
        original = source / 'photo.png'; Image.new('RGB', (80, 60), 'red').save(original)
        before = original.read_bytes()
        self.assertTrue(self.home.open_workspace(source))
        self.assertEqual(list(source.iterdir()), [original])
        page = self.controller.screening_widget; self.fixture.wait_for_screening(page)
        self.assertEqual(self.home.current_root, source)
        self.assertNotEqual(page.workspace.root, source)
        self.assertIn(str(source), page.open_button.toolTip())
        self.assertNotIn(str(page.workspace.root), page.open_button.toolTip())
        self.assertEqual(page.session.items[0].source.read_bytes(), before)
        self.assertTrue(page.session.project_root.is_relative_to(page.workspace.root))
        self.assertFalse((page.session.project_root / 'json' / 'photo.json').exists())
        self.assertEqual(original.read_bytes(), before)
        menu = self.home.home.create_context_menu(str(source))
        actions = {a.objectName(): a for a in menu.actions()}
        self.assertFalse(actions['delete'].isEnabled()); self.assertTrue(actions['remove'].isEnabled())
        self.assertTrue(self.home.remove_workspace(source))
        self.assertIsNone(self.home.current_root)
        self.assertTrue(self.window.close())
        self.assertEqual(list(source.iterdir()), [original]); self.assertEqual(original.read_bytes(), before)

    def test_external_isat_json_is_copied_and_can_open_original_annotation_canvas(self):
        source = self.root / '外部ISAT'
        images = source / 'images'; labels = source / 'json'
        images.mkdir(parents=True); labels.mkdir()
        fixtures = Path(__file__).parents[1] / 'fixtures'
        shutil.copy2(fixtures / 'sample.png', images / 'sample.png')
        shutil.copy2(fixtures / 'sample.json', labels / 'sample.json')
        before = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()}
        self.assertTrue(self.home.open_workspace(source))
        self.assertEqual({str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()}, before)
        page = self.controller.screening_widget; self.fixture.wait_for_screening(page)
        project = page.session.project_root
        self.assertTrue((project / 'json' / 'sample.json').is_file())
        self.assertTrue(self.controller.open_screened_project({'image_root': str(project / 'images'),
                        'label_root': str(project / 'json'), 'files': ['sample.png']}))
        self.assertEqual(len(self.window.polygons), 2)
        self.assertEqual({str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()}, before)

    def test_external_yolo_dataset_is_organized_and_opens_with_private_yaml_and_outputs(self):
        source = self.root / '外部YOLO'; images = source / 'images' / 'train'; images.mkdir(parents=True)
        Image.new('RGB', (80, 60), 'red').save(images / 'photo.png')
        config = source / 'data.yaml'; config.write_text('train: images/train\nnames: [part]\n')
        before = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()}
        self.assertTrue(self.home.open_workspace(source))
        self.assertIs(self.controller.stack.currentWidget(), self.controller.widget)
        train = self.controller.widget.train_tab
        organized = Path(train.tr_data_yaml.currentText())
        self.assertNotEqual(organized, config)
        self.assertTrue(organized.is_relative_to(self.home.storage_root))
        self.assertTrue((organized.parent / 'images/train/photo.png').is_file())
        self.assertFalse(Path(train.tr_results.currentText()).is_relative_to(source))
        self.assertIsNone(train._train_worker)
        self.assertEqual({str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()}, before)

    def test_reopening_external_source_restores_private_project_and_training_draft(self):
        source = self.root / '持久化外部图片'; source.mkdir()
        Image.new('RGB', (80, 60), 'red').save(source / 'photo.png')
        self.assertTrue(self.home.open_workspace(source))
        self.assertEqual(sorted(p.name for p in source.iterdir()), ['photo.png'])
        page = self.controller.screening_widget; self.fixture.wait_for_screening(page)
        project = page.session.project_root
        self.controller.show_development(); self.controller.widget.train_tab.tr_epochs.setValue(44)
        self.home.show_home()
        other = self.home.store.create(self.root, '另一个项目'); self.home.open_workspace(other)
        self.home.show_home(); self.assertTrue(self.home.open_workspace(source))
        self.fixture.wait_for_screening(self.controller.screening_widget)
        self.assertEqual(self.controller.screening_widget.session.project_root, project)
        self.controller.show_development()
        self.assertEqual(self.controller.widget.train_tab.tr_epochs.value(), 44)
        self.assertEqual(len(self.controller.screening_widget.workspace.projects()), 1)
        self.assertEqual(sorted(p.name for p in source.iterdir()), ['photo.png'])

    def test_deleted_external_source_does_not_reappear_on_home_or_exit(self):
        source = self.root / '移走的外部图片'; source.mkdir()
        Image.new('RGB', (80, 60), 'red').save(source / 'photo.png')
        self.assertTrue(self.home.open_workspace(source))
        self.assertEqual(sorted(p.name for p in source.iterdir()), ['photo.png'])
        self.fixture.wait_for_screening(self.controller.screening_widget)
        shutil.rmtree(source)
        self.home.show_home()
        self.assertNotIn(str(source), [row['root'] for row in self.home.store.recent()])
        self.assertTrue(self.window.close()); self.assertFalse(source.exists())

    def test_running_task_blocks_external_open_before_creating_private_storage(self):
        class Worker(QtCore.QThread):
            def run(self):
                while not self.isInterruptionRequested(): self.msleep(5)
        current = self.home.store.create(self.root, '有任务的原项目')
        source = self.root / '待打开的外部目录'; source.mkdir()
        image = source / 'photo.png'; Image.new('RGB', (80, 60), 'red').save(image)
        storage = Path(self.home.store.read_existing(source)['storage_root'])
        self.home.open_workspace(current); page = self.controller.screening_widget
        worker = Worker(); worker.start(); page._scan_worker = worker
        try:
            with patch.object(QtWidgets.QMessageBox, 'warning'):
                self.assertFalse(self.home.open_workspace(source))
            self.assertFalse(storage.exists())
            self.assertEqual(self.home.current_root, current)
            self.assertEqual(list(source.iterdir()), [image])
        finally:
            worker.requestInterruption(); worker.wait(5000); page._scan_worker = None

    def test_external_directory_replaced_during_switch_guard_is_not_opened_or_registered(self):
        source = self.root / '选择后的目录'; source.mkdir()
        Image.new('RGB', (80, 60), 'red').save(source / 'old.png')
        def replace():
            source.rename(self.root / '原目录备份')
            source.mkdir(); Image.new('RGB', (80, 60), 'blue').save(source / 'new.png')
            return True
        with patch.object(self.controller, '_can_replace_annotation', replace), \
             patch.object(QtWidgets.QMessageBox, 'warning'):
            self.assertFalse(self.home.open_workspace(source))
        self.assertIsNone(self.home.current_root)
        self.assertFalse(Path(self.home.store.read_existing(source)['storage_root']).exists())
        self.assertEqual(sorted(p.name for p in source.iterdir()), ['new.png'])

    def test_replaced_current_external_directory_starts_a_new_session_at_same_path(self):
        source = self.root / '当前外部目录'; source.mkdir()
        Image.new('RGB', (80, 60), 'red').save(source / 'old.png')
        self.home.open_workspace(source); self.fixture.wait_for_screening(self.controller.screening_widget)
        old_project = self.controller.screening_widget.session.project_root
        self.controller.show_development(); self.controller.widget.train_tab.tr_epochs.setValue(55)
        source.rename(self.root / '备份当前外部目录')
        source.mkdir(); Image.new('RGB', (80, 60), 'blue').save(source / 'new.png')
        self.home.show_home(); self.assertTrue(self.home.open_workspace(source))
        self.assertIsNone(self.controller.widget)
        self.fixture.wait_for_screening(self.controller.screening_widget)
        self.assertNotEqual(self.controller.screening_widget.session.project_root, old_project)
        self.assertEqual(self.controller.screening_widget.session.items[0].name, 'new.png')
        self.assertTrue(old_project.is_dir())

    def test_cancel_delete_keeps_project_and_current_workspace(self):
        root = self.home.store.create(self.root, '保留项目')
        self.home.open_workspace(root); self.home.show_home()
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.No):
            self.assertFalse(self.home.delete_workspace(str(root)))
        self.assertTrue(root.is_dir()); self.assertEqual(self.home.current_root, root)

    def test_adopted_existing_folder_cannot_be_trashed_even_with_confirmation(self):
        root = self.root / '已有文件目录'; (root / 'projects').mkdir(parents=True)
        original = root / '重要文件.txt'; original.write_text('keep')
        self.home.store.register(root)
        recycle = self.root / 'recycle'; recycle.mkdir()
        def move_to_trash(source):
            destination = recycle / Path(source).name
            shutil.move(source, destination)
            return True, str(destination)
        with patch.object(QtWidgets.QMessageBox, 'warning'), \
             patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.Yes), \
             patch.object(QtCore.QFile, 'moveToTrash', move_to_trash):
            self.assertFalse(self.home.delete_workspace(str(root)))
        self.assertEqual(original.read_text(), 'keep')
        self.assertEqual(list(recycle.iterdir()), [])
        menu = self.home.home.create_context_menu(str(root))
        actions = {a.objectName(): a for a in menu.actions()}
        self.assertFalse(actions['delete'].isEnabled())
        self.assertTrue(actions['remove'].isEnabled())

    def test_remove_current_project_only_forgets_card_and_keeps_all_files(self):
        root = self.home.store.create(self.root, '只移除卡片')
        original = root / '重要文件.txt'; original.write_text('keep')
        self.home.open_workspace(root); self.home.show_home()
        self.assertTrue(self.home.remove_workspace(str(root)))
        self.assertEqual(original.read_text(), 'keep')
        self.assertIsNone(self.home.current_root)
        self.assertNotIn(str(root), [row['root'] for row in self.home.store.recent()])
        from yolo_backprop.workspaces.store import WorkspaceStore
        self.assertNotIn(str(root), [row['root'] for row in WorkspaceStore(self.home.store.path).recent()])
        self.assertTrue(self.window.close())
        self.assertEqual(original.read_text(), 'keep')

    def test_replacing_project_during_confirmation_cannot_delete_the_new_directory(self):
        root = self.home.store.create(self.root, '删除目标')
        old = self.root / '原项目备份'; recycle = self.root / 'recycle'; recycle.mkdir()
        def replace_and_confirm(*args):
            root.rename(old)
            self.home.store.create(self.root, '删除目标')
            (root / '新文件.txt').write_text('keep replacement')
            return QtWidgets.QMessageBox.Yes
        def move_to_trash(source):
            destination = recycle / Path(source).name
            shutil.move(source, destination)
            return True, str(destination)
        with patch.object(QtWidgets.QMessageBox, 'warning'), \
             patch.object(QtWidgets.QMessageBox, 'question', replace_and_confirm), \
             patch.object(QtCore.QFile, 'moveToTrash', move_to_trash):
            self.assertFalse(self.home.delete_workspace(str(root)))
        self.assertEqual((root / '新文件.txt').read_text(), 'keep replacement')
        self.assertTrue(old.is_dir()); self.assertEqual(list(recycle.iterdir()), [])

    def test_external_project_deletion_does_not_block_home_or_recreate_folder_on_exit(self):
        root = self.home.store.create(self.root, '手动删除')
        self.home.open_workspace(root)
        shutil.rmtree(root)
        with patch.object(QtWidgets.QMessageBox, 'warning'):
            self.home.show_home()
            self.assertIs(self.controller.stack.currentWidget(), self.home.home)
            self.assertTrue(self.window.close())
        self.assertFalse(root.exists())

    def test_trash_failure_preserves_current_project_and_history(self):
        root = self.home.store.create(self.root, '删除失败')
        self.home.open_workspace(root); self.home.show_home()
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.Yes), \
             patch.object(QtWidgets.QMessageBox, 'warning'), \
             patch.object(QtCore.QFile, 'moveToTrash', return_value=(False, '')):
            self.assertFalse(self.home.delete_workspace(str(root)))
        self.assertTrue(root.is_dir()); self.assertEqual(self.home.current_root, root)
        self.assertIn(str(root), [row['root'] for row in self.home.store.recent()])

    def test_running_task_blocks_deleting_the_project(self):
        class Worker(QtCore.QThread):
            def run(self):
                while not self.isInterruptionRequested(): self.msleep(5)
        root = self.home.store.create(self.root, '运行中的项目')
        self.home.open_workspace(root); page = self.controller.screening_widget
        worker = Worker(); worker.start(); page._scan_worker = worker
        try:
            with patch.object(QtWidgets.QMessageBox, 'warning'), \
                 patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.Yes):
                self.assertFalse(self.home.delete_workspace(str(root)))
            self.assertTrue(root.is_dir()); self.assertTrue(worker.isRunning())
        finally:
            worker.requestInterruption(); worker.wait(5000); page._scan_worker = None

    def test_cancel_unsaved_annotation_during_delete_keeps_project_and_edits(self):
        root = self.home.store.create(self.root, '未保存的项目')
        self.home.open_workspace(root); self.window.saved = False
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.Cancel):
            self.assertFalse(self.home.delete_workspace(str(root)))
        self.assertTrue(root.is_dir()); self.assertFalse(self.window.saved)
        self.assertEqual(self.home.current_root, root)

    def test_switching_workspaces_keeps_training_drafts_and_output_paths_separate(self):
        a = self.home.store.create(self.root, 'A'); b = self.home.store.create(self.root, 'B')
        c = self.controller
        self.home.open_workspace(a); c.show_development(); c.widget.train_tab.tr_epochs.setValue(23)
        self.home.show_home(); self.assertTrue(self.home.open_workspace(b))
        c.show_development(); c.widget.train_tab.tr_epochs.setValue(7)
        self.assertEqual(c.widget.train_tab.tr_results.currentText(), str(b / 'results'))
        self.assertEqual(c.widget.infer_tab.ir_save.currentText(), str(b / 'predict'))
        self.home.show_home(); self.assertTrue(self.home.open_workspace(a)); c.show_development()
        self.app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
        c.show_annotation(); c.show_development()
        self.assertEqual(c.widget.train_tab.tr_epochs.value(), 23)
        self.assertEqual(c.widget.train_tab.tr_logs.currentText(), str(a / 'logs'))
        self.assertEqual(self.home.store.read(b)['state']['training']['epochs'], 7)

    def test_cancel_unsaved_annotation_switch_keeps_original_workspace_and_canvas(self):
        a = self.home.store.create(self.root, 'A'); b = self.home.store.create(self.root, 'B')
        self.home.open_workspace(a)
        self.controller.show_annotation(); self.window.saved = False
        original = self.window.view
        self.home.show_home()
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.Cancel):
            self.assertFalse(self.home.open_workspace(b))
        self.assertEqual(self.home.current_root, a)
        self.assertIs(self.window.view, original)
        self.assertFalse(self.window.saved)

    def test_running_worker_blocks_switch_but_can_return_to_same_workspace(self):
        class Worker(QtCore.QThread):
            def run(self):
                while not self.isInterruptionRequested(): self.msleep(5)
        a = self.home.store.create(self.root, 'A'); b = self.home.store.create(self.root, 'B')
        self.home.open_workspace(a); c = self.controller
        worker = Worker(); worker.start()
        c.screening_widget._scan_worker = worker
        try:
            self.home.show_home()
            with patch.object(QtWidgets.QMessageBox, 'warning'):
                self.assertFalse(self.home.open_workspace(b))
            self.assertEqual(self.home.current_root, a)
            self.assertTrue(self.home.open_workspace(a))
            self.assertTrue(worker.isRunning())
        finally:
            worker.requestInterruption(); worker.wait(5000)
            c.screening_widget._scan_worker = None

    def test_recent_project_and_training_photo_survive_workspace_switch(self):
        a = self.home.store.create(self.root, 'A'); b = self.home.store.create(self.root, 'B')
        source = self.root / 'source'; source.mkdir()
        image = source / 'photo.png'; Image.new('RGB', (80, 60), 'blue').save(image)
        self.home.open_workspace(a); page = self.controller.screening_widget
        page.open_folder(str(source)); self.fixture.wait_for_screening(page)
        project = page.session.project_root
        config = self.root / 'data.yaml'; config.write_text('train: source\n')
        self.controller.show_development()
        train = self.controller.widget.train_tab
        train.tr_data_yaml.setCurrentText(str(config))
        self.home.record_training(train._build_config_from_train_ui())
        info = self.home.store.read(a)
        self.assertTrue(info['trained']); self.assertTrue(Path(info['cover']).is_file())
        self.home.show_home(); self.home.open_workspace(b)
        self.home.show_home(); self.home.open_workspace(a)
        self.fixture.wait_for_screening(self.controller.screening_widget)
        self.assertEqual(self.controller.screening_widget.session.project_root, project)
        self.assertEqual(self.home.store.read(a)['last_training']['data_yaml'], str(config))

    def test_close_and_restart_restores_workspace_training_draft_from_disk(self):
        root = self.home.store.create(self.root, '持久化空间')
        self.home.open_workspace(root); self.controller.show_development()
        self.controller.widget.train_tab.tr_epochs.setValue(31)
        self.assertTrue(self.window.close()); self.app.processEvents()
        from yolo_backprop.widgets.mainwindow import MainWindow
        reopened = MainWindow(); reopened.show(); self.app.processEvents()
        def cleanup():
            reopened.saved = True
            reopened.check_latest_version_thread.wait(5000)
            reopened.close(); self.app.processEvents()
        self.addCleanup(cleanup)
        second = reopened.model_development
        self.assertIs(second.stack.currentWidget(), second.workspace_home.home)
        self.assertTrue(second.workspace_home.open_workspace(root)); second.show_development()
        self.assertEqual(second.widget.train_tab.tr_epochs.value(), 31)
        self.assertEqual(second.widget.train_tab.tr_results.currentText(), str(root / 'results'))

    def test_real_train_start_updates_home_using_the_actual_training_config(self):
        from yolo_backprop.model_development.gui.workers import TrainWorker
        root = self.home.store.create(self.root, '训练空间')
        images = root / 'training-images'; images.mkdir()
        Image.new('RGB', (80, 60), 'red').save(images / 'sample.png')
        config = root / 'data.yaml'; config.write_text('train: training-images\n')
        weights = root / 'local.pt'; weights.write_bytes(b'fixture; backend not run')
        self.home.open_workspace(root); self.controller.show_development()
        train = self.controller.widget.train_tab
        train.tr_data_yaml.setCurrentText(str(config)); train.tr_model.set_model(str(weights))
        train.tr_device.setCurrentIndex(train.tr_device.findData('cpu'))
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.Yes), \
             patch.object(TrainWorker, 'start', lambda worker: None):
            train._on_start_train()
        self.addCleanup(train._on_train_thread_finished)
        info = self.home.store.read(root)
        self.assertEqual(info['last_training']['data_yaml'], str(config))
        self.assertTrue(info['trained']); self.assertTrue(Path(info['cover']).is_file())

    def test_cancel_unsaved_screening_switch_keeps_working_session(self):
        a = self.home.store.create(self.root, 'A'); b = self.home.store.create(self.root, 'B')
        source = self.root / 'original'; source.mkdir()
        Image.new('RGB', (80, 60), 'red').save(source / 'a.png')
        self.home.open_workspace(a); page = self.controller.screening_widget
        page.open_folder(str(source)); self.fixture.wait_for_screening(page)
        page.grid.setCurrentRow(0); page.command_actions['remove'].trigger()
        self.home.show_home()
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.Cancel):
            self.assertFalse(self.home.open_workspace(b))
        self.assertEqual(self.home.current_root, a)
        self.assertIs(self.controller.screening_widget, page)
        self.assertEqual(len(page.session.trash), 1)
        self.assertTrue((source / 'a.png').is_file())

    def test_late_previous_workspace_signal_does_not_replace_new_workspace_history(self):
        a = self.home.store.create(self.root, 'A'); b = self.home.store.create(self.root, 'B')
        source = self.root / 'original'; source.mkdir()
        Image.new('RGB', (80, 60), 'red').save(source / 'a.png')
        self.home.open_workspace(a); page = self.controller.screening_widget
        page.open_folder(str(source)); self.fixture.wait_for_screening(page)
        session = page.session
        self.home.show_home(); self.home.open_workspace(b)
        page.session_loaded.emit(session)
        info = self.home.store.read(b)
        self.assertNotIn('project_name', info['state'])
        self.assertEqual(info['cover'], '')

    def test_save_finished_in_thread_waits_for_ui_completion_before_workspace_switch(self):
        a = self.home.store.create(self.root, 'A'); b = self.home.store.create(self.root, 'B')
        source = self.root / 'original'; source.mkdir()
        Image.new('RGB', (80, 60), 'red').save(source / 'a.png')
        self.home.open_workspace(a); page = self.controller.screening_widget
        page.open_folder(str(source)); self.fixture.wait_for_screening(page)
        self.assertTrue(page.save_screening())
        self.assertTrue(page._export_worker.wait(5000))
        with patch.object(QtWidgets.QMessageBox, 'warning'):
            self.assertFalse(self.home.open_workspace(b))
        self.assertEqual(self.home.current_root, a)
        self.app.processEvents(); self.app.processEvents()
