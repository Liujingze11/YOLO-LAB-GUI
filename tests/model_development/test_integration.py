import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PyQt5 import QtCore, QtWidgets, QtTest


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        from ISAT.widgets import mainwindow as module
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        directory = Path(self.temp.name)
        original = Path(module.SOFTWARE_CONFIG_FILE).read_bytes()
        self.original_path = Path(module.SOFTWARE_CONFIG_FILE)
        self.original_hash = hashlib.sha256(original).hexdigest()
        software = directory/'software.yaml'; software.write_bytes(original)
        categories = directory/'isat.yaml'; categories.write_text('label:\n- {name: __background__, color: "#000000"}\n- {name: person, color: "#ef2929"}\n- {name: knife, color: "#fcaf3e"}\n')
        for mock in [patch.object(module, 'SOFTWARE_CONFIG_FILE', str(software)), patch.object(module, 'CONFIG_FILE', str(categories)), patch.object(module.CheckLatestVersionThread, 'run', lambda self: None), patch.dict(os.environ, {'ISAT_MODEL_DATA_DIR': str(directory/'model-data'), 'YOLO_BACKPROP_CONFIG_DIR': str(directory/'screening-config')})]:
            mock.start(); self.addCleanup(mock.stop)
        from ISAT.data_screening.workspace import WorkspaceSettings
        WorkspaceSettings().select(directory / 'workspace')
        self.window = module.MainWindow()
        self.addCleanup(self.cleanup_window)
        if not getattr(self, 'start_home', False): self.window.model_development.show_annotation()
        self.window.resize(1280, 900); self.window.show(); self.app.processEvents()

    def cleanup_window(self):
        self.window.saved = True
        controller = getattr(self.window, 'model_development', None)
        if controller and controller.widget:
            controller.widget.stop_workers()
        self.window.check_latest_version_thread.wait(5000)
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.Discard):
            self.window.close(); self.app.processEvents()
        self.assertEqual(hashlib.sha256(self.original_path.read_bytes()).hexdigest(), self.original_hash)

    def controller(self):
        result = getattr(self.window, 'model_development', None)
        self.assertIsNotNone(result, 'model development navigation is installed on original ISAT')
        return result

    def test_workspace_switch_keeps_navigation_and_content_bounds_fixed(self):
        w = self.window; c = self.controller()
        navigation = QtCore.QRect(c.navigation.geometry())
        content = QtCore.QRect(c.stack.geometry())
        self.assertEqual(navigation.top(), 0, 'annotation menus belong inside the content area')
        self.assertTrue(hasattr(c, 'frame'), 'all work pages share a title frame')
        header = QtCore.QRect(c.frame.header.geometry())
        self.assertGreater(content.top(), header.bottom())
        for control in (w.menubar, w.toolBar, w.statusbar, w.categories_dock, w.files_dock):
            bounds = QtCore.QRect(control.mapTo(c.frame, QtCore.QPoint()), control.size())
            self.assertTrue(content.contains(bounds), control.objectName())
        for switch in (c.show_screening, c.show_development, c.show_annotation,
                       c.show_screening, c.show_annotation):
            switch(); self.app.processEvents(); self.app.processEvents()
            self.assertEqual(c.navigation.geometry(), navigation)
            self.assertEqual(c.stack.geometry(), content)
            self.assertEqual(c.frame.header.geometry(), header)

    def test_workbench_header_follows_page_project_and_home(self):
        c = self.controller()
        self.assertTrue(hasattr(c, 'frame'), 'shared title frame is installed')
        root = c.workspace_home.store.create(Path(self.temp.name), '统一项目')
        self.assertTrue(c.workspace_home.open_workspace(root))
        for switch, title in ((c.show_screening, '数据筛选'),
                              (c.show_annotation, '数据标注'),
                              (c.show_development, '模型开发')):
            switch(); self.app.processEvents()
            self.assertTrue(c.frame.header.isVisible())
            self.assertEqual(c.frame.title.text(), title)
            self.assertEqual(c.frame.project.text(), '统一项目')
        c.workspace_home.show_home(); self.app.processEvents()
        self.assertFalse(c.frame.header.isVisible())
        c.workspace_home.open_workspace(root); self.app.processEvents()
        self.assertTrue(c.frame.header.isVisible())
        self.assertEqual(c.frame.project.text(), '统一项目')

    def test_folded_training_options_keep_values_across_page_switches(self):
        c = self.controller(); c.show_development(); self.app.processEvents()
        page = c.widget.train_tab
        self.assertTrue(hasattr(page, 'augmentation_card'), 'augmentation can be folded')
        card = page.augmentation_card
        self.assertFalse(card.toggle.isChecked())
        QtTest.QTest.mouseClick(card.toggle, QtCore.Qt.LeftButton)
        self.app.processEvents()
        self.assertTrue(card.body_scroll.isVisible())
        page.aug_hsv_h.setValue(0.023)
        QtTest.QTest.mouseClick(card.toggle, QtCore.Qt.LeftButton)
        c.show_screening(); c.show_annotation(); c.show_development()
        self.app.processEvents()
        self.assertFalse(card.body_scroll.isVisible())
        self.assertAlmostEqual(page.aug_hsv_h.value(), 0.023)
        card.toggle.setFocus()
        QtTest.QTest.keyClick(card.toggle, QtCore.Qt.Key_Space)
        self.app.processEvents()
        self.assertTrue(card.body_scroll.isVisible())
        self.assertAlmostEqual(page.aug_hsv_h.value(), 0.023)

    def test_theme_switch_applies_to_each_work_page(self):
        from PyQt5 import QtGui
        c = self.controller(); c.show_development(); self.app.processEvents()
        c.widget._change_theme(); self.app.processEvents()
        self.assertGreater(c.frame.title.palette().color(QtGui.QPalette.WindowText).lightness(), 180)
        c.show_screening(); self.app.processEvents()
        self.assertGreater(c.screening_widget.source_label.palette().color(QtGui.QPalette.WindowText).lightness(), 140)
        c.show_annotation(); self.app.processEvents()
        self.assertGreater(self.window.menubar.palette().color(QtGui.QPalette.WindowText).lightness(), 180)
        c.show_development(); c.widget._change_theme(); self.app.processEvents()
        self.assertLess(c.frame.title.palette().color(QtGui.QPalette.WindowText).lightness(), 60)

    def test_training_actions_remain_visible_in_small_window(self):
        c = self.controller(); c.show_development()
        self.window.resize(1100, 760); self.app.processEvents()
        train = c.widget.train_tab
        for control in (train.btn_start, train.btn_stop, train.cb_presets):
            bounds = QtCore.QRect(control.mapTo(self.window, QtCore.QPoint()), control.size())
            self.assertTrue(self.window.rect().contains(bounds), control.text() if hasattr(control, 'text') else 'presets')

    def test_training_group_translation_keeps_folded_state(self):
        from ISAT.model_development.gui.i18n import tr
        c = self.controller(); c.show_development()
        card = c.widget.train_tab.augmentation_card
        try:
            c.widget._language.setCurrentIndex(1)
            self.assertEqual(card.toggle.text(), tr('train.card.augment'))
            self.assertFalse(card.toggle.isChecked())
            c.widget._language.setCurrentIndex(0)
            self.assertEqual(card.toggle.text(), tr('train.card.augment'))
        finally:
            c.widget._language.setCurrentIndex(0)

    def test_switch_preserves_real_isat_canvas_polygons_and_hidden_docks(self):
        w = self.window; c = self.controller()
        self.assertIsNone(c.widget, 'model development is lazy')
        fixtures = Path(__file__).parents[1]/'fixtures'
        w.image_root = str(fixtures); w.label_root = str(fixtures); w.files_list = ['sample.png']; w.current_index = 0
        w.files_dock_widget.update_widget(); w.show_image(0); self.app.processEvents()
        w.view.scale(1.3, 1.3); w.text_prompt_dock.hide()
        original_view = w.view; original_scene = w.scene
        objects = list(w.polygons); self.assertEqual(len(objects), 2)
        before = w.view.transform(); center = w.view.mapToScene(w.view.viewport().rect().center())
        w.saved = False
        capture = Path(__file__).parents[2]/'.runtime/test-captures'
        capture.mkdir(parents=True, exist_ok=True)
        w.grab().save(str(capture/'annotation.png'))
        c.show_development(); self.app.processEvents()
        w.grab().save(str(capture/'model-development.png'))
        self.assertIs(w.view, original_view); self.assertIs(w.scene, original_scene)
        self.assertEqual(w.polygons, objects); self.assertFalse(w.saved)
        self.assertTrue(w.categories_dock.isHidden())
        c.widget.train_tab.tr_epochs.setValue(23)
        c.show_annotation(); self.app.processEvents(); self.app.processEvents()
        self.assertIs(w.view.scene(), original_scene); self.assertEqual(w.polygons, objects)
        self.assertAlmostEqual(w.view.transform().m11(), before.m11(), places=6)
        restored = w.view.mapToScene(w.view.viewport().rect().center())
        self.assertAlmostEqual(restored.x(), center.x(), delta=2)
        self.assertAlmostEqual(restored.y(), center.y(), delta=2)
        self.assertTrue(w.text_prompt_dock.isHidden()); self.assertFalse(w.categories_dock.isHidden())
        c.show_development(); self.app.processEvents()
        self.assertEqual(c.widget.train_tab.tr_epochs.value(), 23)
        c.show_annotation(); self.app.processEvents()
        w.saved = True

    def test_annotation_shortcuts_do_not_run_inside_model_inputs(self):
        w = self.window; c = self.controller()
        shortcut = w.actionPolygon.shortcut().toString(); self.assertEqual(shortcut, 'C')
        c.show_development(); self.app.processEvents()
        self.assertTrue(w.actionPolygon.shortcut().isEmpty())
        field = c.widget.train_tab.tr_exp; field.clear(); field.setFocus()
        before = w.scene.mode
        QtTest.QTest.keyClicks(field, 'cat'); self.app.processEvents()
        self.assertEqual(field.text(), 'cat'); self.assertEqual(w.scene.mode, before)
        c.show_annotation(); self.app.processEvents()
        self.assertEqual(w.actionPolygon.shortcut().toString(), shortcut)

    def test_navigation_keeps_four_actions_and_existing_page_switches(self):
        c = self.controller()
        actions = [action for action in c.navigation.actions() if not action.isSeparator()]
        self.assertEqual(actions, [c.home_action, c.screening_action, c.annotation_action, c.development_action])
        for action, page in ((c.screening_action, 'screening_widget'),
                             (c.development_action, 'widget'), (c.annotation_action, 'annotation_view')):
            QtTest.QTest.mouseClick(c.navigation.widgetForAction(action), QtCore.Qt.LeftButton)
            self.app.processEvents()
            self.assertIs(c.stack.currentWidget(), getattr(c, page))
            self.assertTrue(action.isChecked())
        QtTest.QTest.mouseClick(c.navigation.widgetForAction(c.home_action), QtCore.Qt.LeftButton)
        self.assertIs(c.stack.currentWidget(), c.workspace_home.home)

    def wait_for_screening(self, page):
        import time
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            self.app.processEvents()
            if page.session is not None and not page.active_workers():
                self.app.processEvents()
                if not page.active_workers(): return
            time.sleep(.01)
        self.fail('screening worker did not finish')

    def test_screening_navigation_preserves_annotation_and_model_form(self):
        w = self.window; c = self.controller()
        fixtures = Path(__file__).parents[1] / 'fixtures'
        w.image_root = str(fixtures); w.label_root = str(fixtures)
        w.files_list = ['sample.png']; w.current_index = 0
        w.files_dock_widget.update_widget(); w.show_image(0)
        polygons = list(w.polygons); view = w.view; w.saved = False
        c.show_screening(); self.app.processEvents()
        self.assertTrue(c.screening_action.isChecked())
        self.assertIs(c.stack.currentWidget(), c.screening_widget)
        self.assertTrue(w.actionPolygon.shortcut().isEmpty())
        self.assertTrue(w.categories_dock.isHidden())
        c.screening_widget.open_folder(str(fixtures)); self.wait_for_screening(c.screening_widget)
        c.show_development(); self.app.processEvents()
        c.widget.train_tab.tr_epochs.setValue(23)
        c.show_screening(); self.app.processEvents()
        self.assertEqual(c.screening_widget.grid.count(), 1)
        c.show_annotation(); self.app.processEvents()
        self.assertIs(w.view, view); self.assertEqual(w.polygons, polygons)
        self.assertFalse(w.saved)
        self.assertEqual(w.actionPolygon.shortcut().toString(), 'C')
        c.show_development(); self.app.processEvents()
        self.assertEqual(c.widget.train_tab.tr_epochs.value(), 23)
        w.saved = True

    def test_screening_import_opens_real_canvas_and_saves_json_separately(self):
        from PIL import Image
        w = self.window; c = self.controller()
        source = Path(self.temp.name) / '原图'; source.mkdir()
        Image.new('RGB', (80, 60), 'red').save(source / 'a.png')
        Image.new('RGB', (80, 60), 'blue').save(source / 'b.png')
        c.show_screening(); page = c.screening_widget
        purge_prompt = patch.object(page, '_confirm_purge', return_value=False)
        purge_prompt.start(); self.addCleanup(purge_prompt.stop)
        page.open_folder(str(source)); self.wait_for_screening(page)
        page.grid.setCurrentRow(1); page.command_actions['remove'].trigger()
        with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=self.temp.name):
            page.import_button.click()
        self.wait_for_screening(page); self.app.processEvents()
        self.assertEqual(w.files_list, ['a.png'])
        self.assertEqual(Path(w.image_root).name, 'images')
        self.assertEqual(Path(w.label_root).name, 'json')
        self.assertIs(c.stack.currentWidget(), c.annotation_view)
        self.assertEqual(w.current_label.img_name, 'a.png')
        self.assertFalse(list(Path(w.label_root).glob('*.json')))
        w.save()
        self.assertTrue((Path(w.label_root) / 'a.json').is_file())
        self.assertFalse((Path(w.image_root) / 'a.json').exists())
        self.assertEqual(sorted(p.name for p in source.iterdir()), ['a.png', 'b.png'])

    def test_saving_screening_updates_current_annotation_file_list_and_clears_empty_canvas(self):
        from PIL import Image
        w = self.window; c = self.controller()
        source = Path(self.temp.name) / 'original'; source.mkdir()
        for name in ('a.png', 'b.png'): Image.new('RGB', (80, 60), 'red').save(source / name)
        c.show_screening(); page = c.screening_widget
        with patch.object(page, '_confirm_purge', return_value=False):
            page.open_folder(str(source)); self.wait_for_screening(page)
            page.import_button.click(); self.wait_for_screening(page)
            w.save()
            c.show_screening()
            page._export_worker = object()  # Save remains in progress until its queued completion is handled.
            try:
                with patch.object(QtWidgets.QMessageBox, 'warning'):
                    c.show_annotation()
                self.assertIs(c.stack.currentWidget(), page)
            finally:
                page._export_worker = None
            c.show_screening(); page.grid.setCurrentRow(0); page.command_actions['remove'].trigger()
            page.save_button.click(); self.wait_for_screening(page)
            self.assertEqual(w.files_list, ['b.png'])
            self.assertEqual(w.current_label.img_name, 'b.png')
            self.assertIs(c.stack.currentWidget(), page)
            page.grid.selectAll(); page.command_actions['remove'].trigger()
            page.save_button.click(); self.wait_for_screening(page)
            self.assertEqual(w.files_list, [])
            self.assertIsNone(w.current_label)

    def test_screening_import_cancel_preserves_unsaved_canvas(self):
        from ISAT.data_screening.session import ScreeningSession
        from PIL import Image
        w = self.window; c = self.controller()
        source = Path(self.temp.name) / 'source'; source.mkdir()
        Image.new('RGB', (80, 60), 'red').save(source / 'a.png')
        result = ScreeningSession.scan(source).export_project(Path(self.temp.name) / 'project')
        c.show_screening(); w.saved = False
        original_root = w.image_root
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.Cancel):
            self.assertFalse(c.open_screened_project(result))
        self.assertEqual(w.image_root, original_root)
        self.assertFalse(w.saved)
        self.assertIs(c.stack.currentWidget(), c.screening_widget)
        w.saved = True

    def test_screening_import_waits_for_running_sam_worker(self):
        class BusyWorker(QtCore.QThread):
            def run(self):
                while not self.isInterruptionRequested(): self.msleep(5)
        from ISAT.data_screening.session import ScreeningSession
        from PIL import Image
        w = self.window; c = self.controller()
        source = Path(self.temp.name) / 'source'; source.mkdir()
        Image.new('RGB', (80, 60), 'red').save(source / 'a.png')
        result = ScreeningSession.scan(source).export_project(Path(self.temp.name) / 'project')
        worker = BusyWorker(); worker.start()
        try:
            with patch.object(w, 'seganythread', worker, create=True), patch.object(QtWidgets.QMessageBox, 'warning', return_value=QtWidgets.QMessageBox.Ok):
                self.assertFalse(c.open_screened_project(result))
                self.assertIsNone(w.image_root)
                self.assertEqual(w.files_list, [])
        finally:
            worker.requestInterruption(); worker.wait(5000)

    def test_screening_own_actions_survive_workspace_shortcut_isolation(self):
        c = self.controller(); w = self.window
        c.show_screening(); self.app.processEvents()
        page = c.screening_widget
        self.assertEqual(page.command_actions['compare'].shortcut().toString(), 'C')
        page.update_shortcuts({'fit': 'G'})
        c.show_annotation(); self.app.processEvents()
        self.assertEqual(w.actionPolygon.shortcut().toString(), 'C')
        c.show_screening(); self.app.processEvents()
        self.assertEqual(page.command_actions['fit'].shortcut().toString(), 'G')
        self.assertTrue(w.actionPolygon.shortcut().isEmpty())

    def test_gpu_guard_keeps_cpu_available_and_checks_local_remote_decoder(self):
        from types import SimpleNamespace
        c = self.controller(); w = self.window
        with patch.object(w, 'use_segment_anything', True), patch.object(w, 'segany', SimpleNamespace(device='cuda'), create=True):
            self.assertTrue(c.job_block_reason('0'))
            self.assertEqual(c.job_block_reason('cpu'), '')
            with patch.object(w, 'use_remote_sam', True):
                self.assertTrue(c.job_block_reason('0'), 'remote encoding can still keep a decoder on the local GPU')

    def test_close_cancel_keeps_unsaved_annotation_window_open(self):
        self.window.saved = False
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.Cancel):
            self.assertFalse(self.window.close())
        self.assertTrue(self.window.isVisible())
        self.assertFalse(self.window.saved)

    def test_saved_annotation_dataset_is_connected_to_training_form(self):
        import shutil
        import json
        import time
        from PIL import Image
        w = self.window; c = self.controller()
        root = Path(self.temp.name)/'图片 数据'; root.mkdir()
        labels = Path(self.temp.name)/'标注 数据'; labels.mkdir()
        fixtures = Path(__file__).parents[1]/'fixtures'
        for i in range(3):
            name = f'image{i}'
            Image.new('RGB', (512, 384), (30 * i, 80, 90)).save(root/(name+'.png'))
            raw = json.loads((fixtures/'sample.json').read_text()); raw['info']['name'] = name+'.png'
            (labels/(name+'.json')).write_text(json.dumps(raw))
        w.image_root = str(root); w.label_root = str(labels); w.files_list = ['image0.png']; w.current_index = 0
        w.files_dock_widget.update_widget(); w.show_image(0); self.app.processEvents()
        w.info_dock_widget.lineEdit_note.setText('保存后再生成训练集'); w.saved = False
        self.assertTrue(hasattr(c, 'create_dataset_dialog'), 'current ISAT data can be prepared for training')
        dialog = c.create_dataset_dialog()
        self.assertTrue(w.saved)
        self.assertEqual(json.loads((labels/'image0.json').read_text())['info']['note'], '保存后再生成训练集')
        destination = Path(self.temp.name)/'训练 输入'
        dialog.destination.setText(str(destination)); dialog.start()
        deadline = time.monotonic() + 10
        while dialog.worker.isRunning() and time.monotonic() < deadline:
            self.app.processEvents(); time.sleep(.02)
        self.assertTrue(dialog.worker.wait(1000)); self.app.processEvents()
        self.assertEqual(c.widget.train_tab.tr_data_yaml.currentText(), str(destination/'data.yaml'))
        self.assertTrue((destination/'manifest.json').is_file())
        dialog.close()

    def test_optional_panel_dependency_error_keeps_annotation_available(self):
        c = self.controller()
        from ISAT.model_development import widget
        with patch.object(widget, 'ModelDevelopmentWidget', side_effect=ModuleNotFoundError('matplotlib')), patch.object(QtWidgets.QMessageBox, 'critical', return_value=QtWidgets.QMessageBox.Ok):
            self.assertFalse(c.show_development())
        self.assertIsNone(c.widget)
        self.assertTrue(c.annotation_action.isChecked())
        self.assertIs(c.stack.currentWidget(), c.annotation_view)
        self.assertTrue(self.window.view.isVisible())

    def test_release_idle_sam_frees_model_references_and_encoder_cache(self):
        from types import SimpleNamespace
        c = self.controller(); w = self.window
        self.assertTrue(callable(getattr(c, 'release_sam', None)), 'SAM can be released before a GPU development job')
        encoder = QtCore.QThread(); encoder.results_dict = {0: 'encoded feature cache'}
        with patch.object(w, 'segany', SimpleNamespace(device='cuda'), create=True), patch.object(w, 'segany_video', object(), create=True), patch.object(w, 'seganythread', encoder, create=True), patch.object(w, 'use_segment_anything', True), patch.object(w, 'use_segment_anything_video', True):
            view = w.view
            self.assertTrue(c.release_sam())
            self.assertIsNone(w.segany); self.assertIsNone(w.segany_video)
            self.assertEqual(encoder.results_dict, {})
            self.assertFalse(w.use_segment_anything); self.assertFalse(w.use_segment_anything_video)
            self.assertIs(w.view, view); self.assertEqual(c.job_block_reason('0'), '')

    def test_gpu_development_job_blocks_loading_sam_from_annotation_page(self):
        import sys
        from ISAT.model_development.gui.workers import ToolWorker
        w = self.window; c = self.controller(); c.show_development()
        worker = ToolWorker([sys.executable, '-c', 'import time;time.sleep(90)'])
        c.widget.train_tab._train_worker = worker
        c.widget.train_tab._job_device = '0'
        worker.start()
        try:
            c.show_annotation(); self.app.processEvents()
            local = Path(self.temp.name)/'model.pth'; local.write_bytes(b'stub model, never loaded')
            with patch.object(w.init_segany_thread, 'start', return_value=None), patch.object(QtWidgets.QMessageBox, 'warning', return_value=QtWidgets.QMessageBox.Ok):
                w.init_segment_anything(str(local))
            self.assertTrue(w.isEnabled(), 'blocked SAM load must leave the annotation window usable')
        finally:
            worker.stop(); worker.wait(8000); w.setEnabled(True)
