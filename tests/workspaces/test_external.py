import json
from pathlib import Path
import shutil
import tempfile
import unittest

from PIL import Image


class ExternalProjectTests(unittest.TestCase):
    def setUp(self):
        from ISAT.workspaces.store import WorkspaceStore
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / '外部图片'; self.root.mkdir()
        self.store = WorkspaceStore(self.base / 'config' / 'workspaces.json')

    def image(self, root=None, name='sample.png'):
        root = self.root if root is None else root
        root.mkdir(parents=True, exist_ok=True)
        path = root / name
        Image.new('RGB', (80, 60), 'red').save(path)
        return path

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def yolo(self):
        self.image(self.root / 'images' / 'train')
        self.image(self.root / 'images' / 'val')
        labels = self.root / 'labels' / 'train'; labels.mkdir(parents=True)
        (labels / 'sample.txt').write_text('0 0.5 0.5 0.2 0.2\n')
        (self.root / 'data.yaml').write_text('train: images/train\nval: images/val\nnames: [part]\n')

    def test_images_without_marker_or_annotation_structure_can_be_selected_read_only(self):
        self.image(); before = self.snapshot()
        info = self.store.read_existing(self.root)
        self.assertTrue(info['external']); self.assertEqual(info['root'], str(self.root))
        self.assertEqual(info['source_images'], str(self.root))
        self.assertNotEqual(info['storage_root'], str(self.root))
        self.assertFalse(Path(info['storage_root']).exists())
        self.assertFalse(self.store.path.exists())
        self.assertEqual(self.snapshot(), before)

    def test_external_state_and_cover_persist_separately_and_source_is_never_deletable(self):
        from ISAT.workspaces.store import MARKER, WorkspaceStore
        image = self.image(); before = self.snapshot()
        self.store.open_location(self.root)
        self.store.update(self.root, state={'training': {'epochs': 39}})
        self.store.set_cover(self.root, image)
        reopened = WorkspaceStore(self.store.path)
        info = reopened.recent()[0]
        self.assertEqual(info['root'], str(self.root))
        self.assertEqual(info['state']['training']['epochs'], 39)
        self.assertTrue((Path(info['storage_root']) / MARKER).is_file())
        self.assertTrue(Path(info['cover']).is_relative_to(Path(info['storage_root'])))
        with self.assertRaises(ValueError): reopened.validate_deletion(self.root)
        self.assertEqual(self.snapshot(), before)
        reopened.forget(self.root)
        self.assertEqual(reopened.recent(), [])
        self.assertEqual(self.snapshot(), before)

    def test_external_source_removal_hides_record_and_never_recreates_source(self):
        self.image(); self.store.open_location(self.root)
        shutil.rmtree(self.root)
        self.assertEqual(self.store.recent(), [])
        with self.assertRaises(ValueError): self.store.update(self.root, state={})
        self.assertFalse(self.root.exists())

    def test_replacement_directory_at_same_path_does_not_inherit_old_private_work(self):
        self.image(); self.store.open_location(self.root)
        self.store.update(self.root, state={'training': {'epochs': 39}})
        old_storage = self.store.read(self.root)['storage_root']
        self.root.rename(self.base / '原目录备份')
        self.root.mkdir(); self.image(name='different.png')
        info = self.store.read_existing(self.root)
        self.assertEqual(info['state'], {})
        self.assertNotEqual(info['storage_root'], old_storage)
        self.assertTrue(Path(old_storage).is_dir())

    def test_isat_images_and_json_are_valid_without_software_marker(self):
        self.image(self.root / 'images')
        labels = self.root / 'json'; labels.mkdir()
        label = labels / 'sample.json'
        label.write_text(json.dumps({'info': {'description': 'ISAT', 'width': 80, 'height': 60}, 'objects': []}))
        before = self.snapshot()
        info = self.store.read_existing(self.root)
        self.assertEqual(info['source_kind'], 'isat')
        self.assertEqual(info['source_images'], str(self.root / 'images'))
        self.assertEqual(self.snapshot(), before)
        label.write_text(json.dumps({'info': {'description': 'ISAT', 'width': 81, 'height': 60}, 'objects': []}))
        with self.assertRaises(ValueError): self.store.read_existing(self.root)

    def test_nested_isat_json_is_matched_and_invalid_annotations_are_rejected(self):
        self.image(self.root / 'images' / 'train')
        labels = self.root / 'json' / 'train'; labels.mkdir(parents=True)
        label = labels / 'sample.json'
        label.write_text('{broken')
        with self.assertRaises(ValueError): self.store.read_existing(self.root)

    def test_isat_object_records_require_real_categories_and_finite_polygon_coordinates(self):
        self.image()
        label = self.root / 'sample.json'
        for objects in ([5], [{'category': 'part', 'segmentation': [[0, 0], [10, 10]]}],
                        [{'category': 'part', 'segmentation': [[0, 0], [10, float('nan')], [20, 0]]}]):
            with self.subTest(objects=objects):
                label.write_text(json.dumps({'info': {'description': 'ISAT', 'width': 80, 'height': 60},
                                             'objects': objects}))
                with self.assertRaises(ValueError): self.store.read_existing(self.root)

    def test_yolo_text_lists_and_string_category_keys_are_supported_but_boolean_keys_are_not(self):
        self.yolo()
        (self.root / 'train.txt').write_text('images/train/sample.png\n')
        config = self.root / 'data.yaml'
        config.write_text('train: train.txt\nnames: {"0": part}\n')
        self.assertEqual(self.store.read_existing(self.root)['source_kind'], 'yolo')
        config.write_text('train: train.txt\nnames: {false: part}\n')
        with self.assertRaises(ValueError): self.store.read_existing(self.root)

    def test_valid_yolo_dataset_is_recognized_without_modifying_source_or_creating_labels(self):
        self.yolo(); before = self.snapshot()
        info = self.store.read_existing(self.root)
        self.assertEqual(info['source_kind'], 'yolo')
        self.assertEqual(info['dataset_yaml'], str(self.root / 'data.yaml'))
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.root / 'labels' / 'val').exists(), 'unlabelled images must remain unlabelled')

    def test_bad_yolo_paths_categories_and_labels_are_rejected_without_fallback(self):
        self.yolo()
        config = self.root / 'data.yaml'; label = self.root / 'labels' / 'train' / 'sample.txt'
        for document in ('train: missing\nnames: [part]\n',
                         'train: images/train\nnames: []\n', 'not: [valid'):
            with self.subTest(document=document):
                config.write_text(document)
                with self.assertRaises(ValueError): self.store.read_existing(self.root)
        config.write_text('train: images/train\nnames: [part]\n')
        for row in ('1 0.5 0.5 0.2 0.2', '0 nan 0.5 0.2 0.2', '0 1.5 0.5 0.2 0.2', '0 0.5'):
            with self.subTest(row=row):
                label.write_text(row)
                with self.assertRaises(ValueError): self.store.read_existing(self.root)

    def test_empty_lookalike_corrupt_images_and_symlinks_are_not_projects(self):
        from ISAT.workspaces.store import MARKER
        (self.root / 'projects').mkdir()
        with self.assertRaises(ValueError): self.store.read_existing(self.root)
        bad = self.root / 'bad.jpg'; bad.write_bytes(b'not an image')
        with self.assertRaises(ValueError): self.store.read_existing(self.root)
        bad.unlink(); source = self.image(self.base / 'elsewhere')
        (self.root / 'linked.png').symlink_to(source)
        with self.assertRaises(ValueError): self.store.read_existing(self.root)
        self.image(); (self.root / MARKER).write_text('{broken')
        with self.assertRaises(ValueError): self.store.read_existing(self.root)
