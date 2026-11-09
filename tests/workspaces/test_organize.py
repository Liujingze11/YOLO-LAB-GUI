import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
import yaml

from yolo_backprop.workspaces.store import WorkspaceStore
from yolo_backprop.data_screening.workers import Cancelled


class OrganizeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'source'; self.root.mkdir()
        self.store = WorkspaceStore(self.base / 'config' / 'workspaces.json')
        for split in ('train', 'val'):
            images = self.root / 'images' / split; images.mkdir(parents=True)
            Image.new('RGB', (40, 30), 'red').save(images / 'part.png')
        labels = self.root / 'labels' / 'train'; labels.mkdir(parents=True)
        (labels / 'part.txt').write_text('1 0.5 0.5 0.25 0.25\n')
        (self.root / 'data.yaml').write_text('train: images/train\nval: images/val\nnames: {1: second, 0: first}\n')

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def organize(self, **kwargs):
        from yolo_backprop.workspaces.organize import organize_yolo
        info = self.store.read_existing(self.root)
        return Path(organize_yolo(info, **kwargs))

    def test_private_dataset_keeps_splits_category_indices_and_unlabelled_images(self):
        original = self.snapshot(); config = self.organize()
        self.assertFalse(config.is_relative_to(self.root))
        data = yaml.safe_load(config.read_text())
        self.assertEqual(data['names'], ['first', 'second'])
        self.assertEqual(data['train'], 'images/train'); self.assertEqual(data['val'], 'images/val')
        self.assertNotIn('path', data)
        self.assertEqual((config.parent / 'labels/train/part.txt').read_text(), '1 0.5 0.5 0.25 0.25\n')
        self.assertTrue((config.parent / 'images/val/part.png').is_file())
        self.assertFalse((config.parent / 'labels/val/part.txt').exists())
        self.assertEqual(self.snapshot(), original)

    def test_duplicate_names_from_lists_are_renamed_with_matching_labels(self):
        images = self.root / 'images/train/batch'; images.mkdir()
        Image.new('RGB', (50, 40), 'blue').save(images / 'part.png')
        labels = self.root / 'labels/train/batch'; labels.mkdir()
        (labels / 'part.txt').write_text('0 0.5 0.5 0.5 0.5\n')
        (self.root / 'train.txt').write_text('images/train/part.png\nimages/train/batch/part.png\n')
        (self.root / 'data.yaml').write_text('train: train.txt\nnames: [first, second]\n')
        config = self.organize()
        self.assertEqual(sorted(p.name for p in (config.parent / 'images/train').iterdir()), ['part.png', 'part_2.png'])
        self.assertTrue((config.parent / 'labels/train/part_2.txt').read_text().startswith('0 '))
        with Image.open(config.parent / 'images/train/part_2.png') as image:
            self.assertEqual(image.size, (50, 40))

    def test_cancellation_leaves_no_partial_dataset_and_originals_are_unchanged(self):
        original = self.snapshot(); stopped = [False]
        def check():
            if stopped[0]: raise Cancelled()
        def progress(*args): stopped[0] = True
        with self.assertRaises(Cancelled): self.organize(check_cancelled=check, progress=progress)
        storage = Path(self.store.read_existing(self.root)['storage_root'])
        self.assertFalse((storage / 'dataset').exists())
        self.assertEqual(list(storage.glob('.dataset-*')), [])
        self.assertEqual(self.snapshot(), original)

    def test_source_change_during_copy_is_detected_and_stage_removed(self):
        label = self.root / 'labels/train/part.txt'
        def change(*args): label.write_text('0 0.5 0.5 0.25 0.25\n')
        with self.assertRaisesRegex(ValueError, '变化'): self.organize(progress=change)
        storage = Path(self.store.read_existing(self.root)['storage_root'])
        self.assertFalse((storage / 'dataset').exists())
        self.assertEqual(list(storage.glob('.dataset-*')), [])

    def test_reopen_reuses_completed_copy_without_overwriting_local_edits(self):
        config = self.organize()
        label = config.parent / 'labels/train/part.txt'; label.write_text('0 0.4 0.4 0.2 0.2\n')
        self.assertEqual(self.organize(), config)
        self.assertEqual(label.read_text(), '0 0.4 0.4 0.2 0.2\n')

    def test_unowned_existing_destination_is_not_adopted_or_overwritten(self):
        destination = Path(self.store.read_existing(self.root)['storage_root']) / 'dataset'
        destination.mkdir(parents=True); (destination / 'keep.txt').write_text('keep')
        with self.assertRaises(ValueError): self.organize()
        self.assertEqual((destination / 'keep.txt').read_text(), 'keep')

    def test_recognition_reports_unique_images_labels_and_rejects_ambiguous_configs(self):
        info = self.store.read_existing(self.root)
        self.assertEqual(info['image_count'], 2); self.assertEqual(info['annotation_count'], 1)
        (self.root / 'dataset.yaml').write_bytes((self.root / 'data.yaml').read_bytes())
        with self.assertRaisesRegex(ValueError, '多个'): self.store.read_existing(self.root)

    def test_custom_yaml_name_is_detected_but_unconfigured_yolo_is_not_treated_as_plain_images(self):
        (self.root / 'data.yaml').rename(self.root / '零件.yaml')
        self.assertEqual(self.store.read_existing(self.root)['source_kind'], 'yolo')
        (self.root / '零件.yaml').unlink()
        with self.assertRaisesRegex(ValueError, 'YOLO'): self.store.read_existing(self.root)

    def test_linked_label_directories_are_rejected_instead_of_silently_importing_external_labels(self):
        labels = self.root / 'labels'
        moved = self.base / 'moved-labels'; labels.rename(moved); labels.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(ValueError): self.store.read_existing(self.root)

    def test_dangling_yolo_label_is_not_mistaken_for_an_unlabelled_image(self):
        label = self.root / 'labels/train/part.txt'; label.unlink(); label.symlink_to(self.base / 'missing.txt')
        with self.assertRaises(ValueError): self.store.read_existing(self.root)
