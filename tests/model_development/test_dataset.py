import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from PIL import Image

try:
    from yolo_backprop.model_development.dataset import prepare_dataset, DatasetCancelled
except ImportError:
    prepare_dataset = None
    DatasetCancelled = RuntimeError


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(prepare_dataset), 'ISAT training dataset preparation is implemented')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'中文 图像'; self.root.mkdir()
        self.labels = Path(self.temp.name)/'标注'; self.labels.mkdir()
        self.categories = ['__background__', 'person', 'knife']
        original = json.loads((Path(__file__).parents[1]/'fixtures/sample.json').read_text())
        self.before = {}
        for i in range(6):
            name = f'样本 {i}'
            Image.new('RGB', (512, 384), (i * 30, 60, 100)).save(self.root/(name+'.png'))
            document = json.loads(json.dumps(original)); document['info']['name'] = name+'.png'
            if i == 4: document['objects'] = []
            if i != 5: (self.labels/(name+'.json')).write_text(json.dumps(document, ensure_ascii=False))
        for path in [*self.root.iterdir(), *self.labels.iterdir()]: self.before[path] = path.read_bytes()

    def prepare(self, name='输出 数据', **options):
        return prepare_dataset(self.root, self.labels, Path(self.temp.name)/name, self.categories, **options)

    def test_missing_labels_are_excluded_and_original_sources_remain_unchanged(self):
        result = self.prepare()
        self.assertEqual(len(result['train']) + len(result['val']), 5)
        self.assertEqual(result['skipped'], ['样本 5.png'])
        target = Path(result['data_yaml']).parent
        manifest = json.loads((target/'manifest.json').read_text())
        self.assertEqual(manifest['categories'], ['person', 'knife'])
        labels = list((target/'labels').rglob('*.txt'))
        self.assertEqual(len(labels), 5)
        self.assertEqual(sum(not p.read_text().strip() for p in labels), 1)
        for path, raw in self.before.items(): self.assertEqual(path.read_bytes(), raw)
        for record in manifest['assets']:
            self.assertEqual((target/record['annotation']).read_bytes(), self.before[Path(record['label_source'])])
            self.assertEqual(hashlib.sha256((target/record['image']).read_bytes()).hexdigest(), record['image_sha256'])

    def test_seeded_split_and_class_indices_are_reproducible(self):
        a = self.prepare('a', seed=17, val_ratio=.4)
        b = self.prepare('b', seed=17, val_ratio=.4)
        self.assertEqual(a['train'], b['train']); self.assertEqual(a['val'], b['val'])
        self.assertFalse(set(a['train']) & set(a['val']))
        for label in (Path(a['data_yaml']).parent/'labels').rglob('*.txt'):
            for line in label.read_text().splitlines():
                fields = line.split(); self.assertIn(fields[0], ['0', '1'])
                self.assertTrue(all(0 <= float(x) <= 1 for x in fields[1:]))

    def test_cancel_or_validation_failure_never_publishes_half_a_dataset(self):
        calls = 0
        def cancel():
            nonlocal calls
            calls += 1
            if calls > 4: raise DatasetCancelled('cancelled')
        destination = Path(self.temp.name)/'cancelled'
        with self.assertRaises(DatasetCancelled): self.prepare('cancelled', check_cancelled=cancel)
        self.assertFalse(destination.exists())
        self.assertFalse(list(destination.parent.glob('.cancelled-*')))
        with self.assertRaises(ValueError):
            prepare_dataset(self.root, self.labels, destination, ['wrong-category'])
        self.assertFalse(destination.exists())

    def test_duplicate_stems_are_rejected_instead_of_reusing_one_annotation(self):
        Image.new('RGB', (512, 384)).save(self.root/'样本 0.jpg')
        with self.assertRaisesRegex(ValueError, 'same|同名|stem'):
            self.prepare()
