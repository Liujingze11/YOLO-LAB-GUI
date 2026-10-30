import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
import tempfile
import unittest
from pathlib import Path
from dataclasses import asdict
from PyQt5.QtWidgets import QApplication


class WidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        os.environ['ISAT_MODEL_DATA_DIR'] = cls.temp.name
        cls.app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        try:
            from ISAT.model_development.widget import ModelDevelopmentWidget
        except ModuleNotFoundError as exc:
            self.fail('PyQt5 model development widget is not implemented: '+str(exc))
        self.widget = ModelDevelopmentWidget()
        self.addCleanup(self.widget.close)
        self.addCleanup(self.widget.stop_workers)

    def test_six_real_pages_work_with_pyqt5_and_keep_drafts(self):
        widget = self.widget
        self.assertEqual(widget.tabs.count(), 6)
        widget.train_tab.tr_epochs.setValue(17)
        widget.train_tab.tr_data_yaml.setCurrentText('/中文 数据/data.yaml')
        for index in range(6):
            widget.tabs.setCurrentIndex(index)
            self.app.processEvents()
            self.assertIsNotNone(widget.tabs.currentWidget().layout())
        widget.tabs.setCurrentIndex(0)
        self.assertEqual(widget.train_tab.tr_epochs.value(), 17)
        self.assertEqual(widget.train_tab.tr_data_yaml.currentText(), '/中文 数据/data.yaml')
        self.assertFalse(any(key.startswith('PySide6') for key in sys.modules))

    def test_all_training_fields_roundtrip_into_config(self):
        from ISAT.model_development.core.config import TrainConfig
        config = TrainConfig(data_yaml='/数据/data.yaml', model_file='', results_dir='/输出', log_dir='/日志', device='cpu', epochs=7, imgsz=96, batch=2, experiment_name='测试', lr0=.0012, close_mosaic=3, multi_scale=.25, optimizer='SGD', momentum=.8, weight_decay=.0002, lrf=.02, cos_lr=False, warmup_epochs=1.5, warmup_momentum=.6, dropout=.2, label_smoothing=.1, use_augment=False, hsv_h=.02, hsv_s=.4, hsv_v=.2, degrees=7, translate=.2, scale=.3, shear=2, perspective=.0001, flipud=.1, fliplr=.3, mosaic=.7, mixup=.1, copy_paste=.2)
        self.widget.train_tab._apply_config(config)
        actual = asdict(self.widget.train_tab._build_config_from_train_ui())
        expected = asdict(config)
        # Empty model selection may preserve the default registry item; all other fields must survive.
        actual.pop('model_file'); expected.pop('model_file')
        for key, value in expected.items():
            with self.subTest(key=key):
                if isinstance(value, float): self.assertAlmostEqual(actual[key], value, places=5)
                else: self.assertEqual(actual[key], value)

    def test_export_options_and_translations_are_usable(self):
        from ISAT.model_development.gui.i18n import set_language, apply_language
        export = self.widget.export_tab
        for name in ['onnx', 'engine', 'openvino', 'coreml', 'tflite']:
            export._select_format(name)
            self.assertEqual(export._build_export_config().format, name)
        set_language('en'); apply_language(self.widget)
        self.assertEqual(self.widget.tabs.tabText(0), 'Train')
        set_language('zh'); apply_language(self.widget)
        self.assertEqual(self.widget.tabs.tabText(0), '训练')
