import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile


class EngineOptionTests(unittest.TestCase):
    def test_disabled_augmentation_really_disables_each_transform(self):
        from ISAT.model_development.core.config import TrainConfig
        from ISAT.model_development.core.training import build_train_kwargs
        config = TrainConfig(mosaic=.7, fliplr=.4, hsv_h=.02)
        arguments = build_train_kwargs(config, False)
        for key in ['hsv_h', 'hsv_s', 'hsv_v', 'degrees', 'translate', 'scale', 'shear', 'perspective', 'flipud', 'fliplr', 'mosaic', 'mixup', 'copy_paste']:
            with self.subTest(transform=key): self.assertEqual(arguments.get(key), 0)
        enabled = build_train_kwargs(config, True)
        self.assertEqual(enabled['mosaic'], .7); self.assertEqual(enabled['fliplr'], .4)
        self.assertEqual(config.mosaic, .7)

    def test_unchecked_export_flags_reach_the_subprocess(self):
        from ISAT.model_development.core import export
        builder = getattr(export, 'build_export_arguments', None)
        self.assertTrue(callable(builder), 'explicit export flag transport is implemented')
        cfg = export.ExportConfig(model_path='/模型/best.pt', format='onnx', imgsz=96, output_dir='/输出', dynamic=False, simplify=False, nms=True, opset=13)
        self.assertEqual(builder(cfg), ['--model', '/模型/best.pt', '--format', 'onnx', '--imgsz', '96', '--output-dir', '/输出', '--opset', '13', '--no-dynamic', '--no-simplify', '--nms'])
