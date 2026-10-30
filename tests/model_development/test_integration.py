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
        for mock in [patch.object(module, 'SOFTWARE_CONFIG_FILE', str(software)), patch.object(module, 'CONFIG_FILE', str(categories)), patch.object(module.CheckLatestVersionThread, 'run', lambda self: None), patch.dict(os.environ, {'ISAT_MODEL_DATA_DIR': str(directory/'model-data')})]:
            mock.start(); self.addCleanup(mock.stop)
        self.window = module.MainWindow()
        self.addCleanup(self.cleanup_window)
        self.window.resize(1280, 900); self.window.show(); self.app.processEvents()

    def cleanup_window(self):
        self.window.saved = True
        controller = getattr(self.window, 'model_development', None)
        if controller and controller.widget:
            controller.widget.stop_workers()
        self.window.check_latest_version_thread.wait(5000)
        self.window.close(); self.app.processEvents()
        self.assertEqual(hashlib.sha256(self.original_path.read_bytes()).hexdigest(), self.original_hash)

    def controller(self):
        result = getattr(self.window, 'model_development', None)
        self.assertIsNotNone(result, 'model development navigation is installed on original ISAT')
        return result

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
        capture = Path(__file__).parents[2]/'docs/superpowers/verification/2026-10-30-isat'
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

    def test_gpu_guard_keeps_cpu_and_remote_sam_available(self):
        from types import SimpleNamespace
        c = self.controller(); w = self.window
        with patch.object(w, 'use_segment_anything', True), patch.object(w, 'segany', SimpleNamespace(device='cuda'), create=True):
            self.assertTrue(c.job_block_reason('0'))
            self.assertEqual(c.job_block_reason('cpu'), '')
            with patch.object(w, 'use_remote_sam', True):
                self.assertEqual(c.job_block_reason('0'), '')

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
