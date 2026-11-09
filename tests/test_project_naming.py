import importlib
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]


class ProjectNamingTests(unittest.TestCase):
    def test_legacy_plugin_imports_share_canonical_modules_and_classes(self):
        import yolo_backprop
        for suffix in ('configs', 'widgets.plugin_base', 'widgets.polygon'):
            canonical = importlib.import_module('yolo_backprop.' + suffix)
            legacy = importlib.import_module('ISAT.' + suffix)
            self.assertIs(legacy, canonical)
            self.assertEqual(canonical.__spec__.name, 'yolo_backprop.' + suffix)
        from ISAT.configs import DRAWMode as old_mode
        from yolo_backprop.configs import DRAWMode
        self.assertIs(old_mode.POLYGON, DRAWMode.POLYGON)
        self.assertIs(importlib.import_module('ISAT'), yolo_backprop)

    def test_new_launcher_uses_canonical_module_and_honors_interpreter_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            interpreter = Path(directory) / 'python with spaces'
            interpreter.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            interpreter.chmod(0o755)
            for script, variables in (
                    ('run-yolo-backprop.sh', {'YOLO_BACKPROP_PYTHON': str(interpreter), 'ISAT_PYTHON': '/missing'}),
                    ('run-isat.sh', {'ISAT_PYTHON': str(interpreter)})):
                env = {k: v for k, v in os.environ.items() if k not in ('ISAT_PYTHON', 'YOLO_BACKPROP_PYTHON')}
                result = subprocess.run(['bash', str(ROOT / script), 'a file'], env={**env, **variables},
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.splitlines(), ['-m', 'yolo_backprop.main', 'a file'])

    def test_model_settings_use_new_location_but_reuse_legacy_data(self):
        from yolo_backprop.model_development.paths import data_dir
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True), patch('sys.platform', 'linux'):
            base = Path(directory)
            os.environ['XDG_DATA_HOME'] = str(base)
            self.assertEqual(data_dir(), base / 'yolo-backprop/model-development')
            legacy = base / 'ISAT/model-development'; legacy.mkdir(parents=True)
            (legacy / 'settings.json').write_text('{"epochs": 23}')
            self.assertEqual(data_dir(), legacy)
            os.environ['ISAT_MODEL_DATA_DIR'] = str(base / 'old-override')
            self.assertEqual(data_dir(), base / 'old-override')
            os.environ['YOLO_BACKPROP_MODEL_DATA_DIR'] = str(base / 'new-override')
            self.assertEqual(data_dir(), base / 'new-override')
            self.assertEqual((legacy / 'settings.json').read_text(), '{"epochs": 23}')

    def test_package_metadata_and_entry_point_belong_to_this_project(self):
        with patch('setuptools.setup') as setup:
            runpy.run_path(str(ROOT / 'setup.py'), run_name='__main__')
        info = setup.call_args.kwargs
        self.assertEqual(info['name'], 'yolo-backprop')
        self.assertEqual(info['url'], 'https://github.com/Liujingze11/YOLO-LAB-GUI')
        self.assertIn('yolo-backprop=yolo_backprop.main:main', info['entry_points']['console_scripts'])
        self.assertIn('yolo_backprop', info['packages'])
        self.assertNotIn('ISAT', info['packages'])

    def test_about_dialog_shows_product_and_preserves_upstream_credit(self):
        from PyQt5 import QtWidgets
        from yolo_backprop.widgets.about_dialog import AboutDialog
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        dialog = AboutDialog(None)
        try:
            dialog.retranslateUi(dialog)
            self.assertIn('YOLO-BACKPROP', dialog.label_3.text())
            self.assertIn('Liujingze11/YOLO-LAB-GUI', dialog.label_5.text())
            self.assertIn('yatengLG', dialog.label_5.text())
            self.assertIn('ISAT', dialog.label_5.text())
        finally:
            dialog.close()

    def test_update_check_uses_only_current_project_releases(self):
        from yolo_backprop.widgets.mainwindow import CheckLatestVersionThread
        response = Mock(status_code=200)
        response.json.return_value = {'tag_name': 'v9.9.9'}
        with patch('requests.get', return_value=response) as get:
            worker = CheckLatestVersionThread(None)
            results = []; worker.tag.connect(lambda *args: results.append(args))
            worker.run()
        self.assertEqual(get.call_args.args[0], 'https://api.github.com/repos/Liujingze11/YOLO-LAB-GUI/releases/latest')
        self.assertEqual(results, [(False, '9.9.9')])

    def test_missing_project_release_does_not_offer_an_update(self):
        from yolo_backprop.widgets.mainwindow import CheckLatestVersionThread
        import requests
        with patch('requests.get', side_effect=requests.HTTPError('404')):
            worker = CheckLatestVersionThread(None)
            results = []; worker.tag.connect(lambda *args: results.append(args))
            worker.run()
        self.assertEqual(results, [(True, '')])

    def test_new_and_legacy_plugin_groups_load_each_plugin_once(self):
        from yolo_backprop.widgets.plugin_manager_dialog import PluginManagerDialog
        current, old, duplicate = Mock(), Mock(), Mock()
        current.value = duplicate.value = 'sample.main:Plugin'
        old.value = 'old.main:Plugin'
        entries = Mock()
        entries.select.side_effect = lambda group: [current] if group == 'yolo_backprop.plugins' else [duplicate, old]
        dialog = Mock(plugins=[])
        with patch('yolo_backprop.widgets.plugin_manager_dialog.entry_points', return_value=entries):
            PluginManagerDialog.load_plugins(dialog)
        self.assertEqual(len(dialog.plugins), 2)
        current.load.assert_called_once(); old.load.assert_called_once()
        duplicate.load.assert_not_called()

    def test_sam2_configuration_resolves_canonical_model_classes(self):
        script = '''
from hydra import compose
from hydra.utils import get_class
import yolo_backprop.segment_any.sam2
config = compose(config_name='sam2_hiera_t')
assert config.model._target_.startswith('yolo_backprop.')
assert get_class(config.model._target_).__name__ == 'SAM2Base'
'''
        result = subprocess.run([sys.executable, '-c', script], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
