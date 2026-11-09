import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / '原图 空间'
        self.root.mkdir()

    def image(self, name, color='red'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new('RGB', (80, 60), color).save(path)
        return path

    def scan(self):
        from yolo_backprop.data_screening.session import ScreeningSession
        return ScreeningSession.scan(self.root)

    def test_scan_filters_bad_files_and_resolves_duplicate_stems_recursively(self):
        self.image('a.jpg'); self.image('sub/a.png'); self.image('sub/A.jpg')
        (self.root / 'broken.png').write_bytes(b'not an image')
        (self.root / 'notes.txt').write_text('ignore')
        session = self.scan()
        self.assertEqual(len(session.items), 3)
        self.assertEqual(len({i.name.rsplit('.', 1)[0].casefold() for i in session.items}), 3)
        self.assertEqual(len(session.skipped), 1)
        self.assertTrue(all((i.width, i.height) == (80, 60) for i in session.items))

    def test_remove_and_rename_only_change_screening_records(self):
        a = self.image('a.png'); b = self.image('b.jpg')
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (a, b)}
        session = self.scan()
        session.rename(session.items[0], '保留 01')
        session.remove([session.items[1]])
        self.assertEqual([i.name for i in session.items], ['保留 01.png'])
        for path, digest in before.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        self.assertFalse((self.root / '保留 01.png').exists())

    def test_rename_rejects_collisions_and_path_escape_without_changing_item(self):
        self.image('a.png'); self.image('b.jpg')
        session = self.scan(); item = session.items[0]
        for bad in ('B', '../escape', '', '..', 'bad/name', 'bad\\name'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                session.rename(item, bad)
            self.assertEqual(item.name, 'a.png')

    def test_export_creates_images_json_and_does_not_invent_empty_annotations(self):
        self.image('a.png'); self.image('b.jpg')
        session = self.scan(); session.remove([session.items[1]])
        destination = self.root.parent / '新项目'
        result = session.export_project(destination, categories=[{'name': 'cat', 'color': '#123456'}])
        self.assertEqual(result['files'], ['a.png'])
        self.assertEqual(Path(result['image_root']), destination / 'images')
        self.assertEqual(Path(result['label_root']), destination / 'json')
        self.assertEqual((destination / 'images/a.png').read_bytes(), (self.root / 'a.png').read_bytes())
        self.assertEqual(list((destination / 'json').glob('*.json')), [])
        self.assertTrue((destination / 'json/isat.yaml').is_file())
        self.assertFalse((destination / 'images/b.jpg').exists())

    def test_preserves_isat_annotation_and_updates_renamed_image(self):
        self.image('a.png')
        document = {'info': {'description': 'ISAT', 'name': 'a.png', 'width': 80, 'height': 60}, 'objects': [{'category': 'cat', 'segmentation': [[1, 1], [40, 1], [40, 40]]}]}
        label = self.root / 'a.json'; label.write_text(json.dumps(document))
        original = label.read_bytes()
        session = self.scan(); session.rename(session.items[0], '新名字')
        destination = self.root.parent / 'project'
        session.export_project(destination)
        copied = json.loads((destination / 'json/新名字.json').read_text())
        self.assertEqual(copied['info']['name'], '新名字.png')
        self.assertEqual(copied['objects'], document['objects'])
        self.assertEqual(label.read_bytes(), original)

    def test_cancel_or_changed_source_leaves_no_project_or_temporary_directory(self):
        self.image('a.png'); self.image('b.png')
        session = self.scan(); destination = self.root.parent / 'project'
        def cancel_after_copy(current, total, name):
            if current: raise RuntimeError('cancelled')
        with self.assertRaisesRegex(RuntimeError, 'cancelled'):
            session.export_project(destination, progress=cancel_after_copy)
        self.assertFalse(destination.exists())
        self.assertEqual(sorted(p.name for p in self.root.parent.iterdir()), [self.root.name])
        (self.root / 'a.png').write_bytes(b'changed')
        with self.assertRaises(ValueError): session.export_project(destination)
        self.assertFalse(destination.exists())

    def test_existing_destination_or_empty_selection_is_not_overwritten(self):
        self.image('a.png'); session = self.scan()
        destination = self.root.parent / 'project'; destination.mkdir()
        marker = destination / 'keep.txt'; marker.write_text('keep')
        with self.assertRaises(ValueError): session.export_project(destination)
        self.assertEqual(marker.read_text(), 'keep')
        session.remove(list(session.items))
        with self.assertRaises(ValueError): session.export_project(self.root.parent / 'empty')

    def test_invalid_existing_annotation_aborts_instead_of_silently_dropping_labels(self):
        self.image('a.png'); (self.root / 'a.json').write_text('{broken')
        session = self.scan(); destination = self.root.parent / 'project'
        with self.assertRaises(ValueError): session.export_project(destination)
        self.assertFalse(destination.exists())

    def test_source_changed_after_its_copy_aborts_the_entire_export(self):
        self.image('a.png'); self.image('b.png')
        session = self.scan(); destination = self.root.parent / 'project'
        def change_previous(current, total, name):
            if current == 2: (self.root / 'a.png').write_bytes(b'changed after copy')
        with self.assertRaises(ValueError):
            session.export_project(destination, progress=change_previous)
        self.assertFalse(destination.exists())
