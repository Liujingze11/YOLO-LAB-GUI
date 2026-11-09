import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


class RelocatedToolsTests(unittest.TestCase):
    def test_dataset_tools_preserve_existing_labels_and_move_matching_pairs(self):
        scripts = ROOT/'yolo_backprop/model_development/tools/dataset_tools'
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); images = base/'images/train'; labels = base/'labels/train'
            images.mkdir(parents=True); labels.mkdir(parents=True)
            for i in range(10): Image.new('RGB', (8, 8), (i, 10, 20)).save(images/f'{i}.png')
            original = '0 .1 .1 .8 .1 .8 .8\n'; (labels/'0.txt').write_text(original)
            subprocess.run([sys.executable, str(scripts/'create_empty_labels.py'), '--dataset-dir', str(base)], check=True, capture_output=True, timeout=10)
            self.assertEqual((labels/'0.txt').read_text(), original)
            self.assertEqual(len(list(labels.glob('*.txt'))), 10)
            subprocess.run([sys.executable, str(scripts/'split_train_val/split_random_with_labels.py'), '--dataset-dir', str(base), '--val-ratio', '.2'], check=True, capture_output=True, timeout=10)
            self.assertEqual(len(list((base/'images/train').glob('*.png'))), 8)
            self.assertEqual(len(list((base/'images/val').glob('*.png'))), 2)
            for split in ['train', 'val']:
                self.assertEqual({p.stem for p in (base/'images'/split).glob('*.png')}, {p.stem for p in (base/'labels'/split).glob('*.txt')})

    def test_algorithm_entry_modules_do_not_import_a_qt_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            code = "import sys; from yolo_backprop.model_development.gui import train_engine,infer_engine,export_engine; assert not any(k.startswith(('PyQt5','PySide6')) for k in sys.modules), 'algorithm process imported Qt'"
            result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, env={**os.environ, 'MPLBACKEND': 'Agg', 'YOLO_CONFIG_DIR': temp, 'YOLO_AUTOINSTALL': 'false'}, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
