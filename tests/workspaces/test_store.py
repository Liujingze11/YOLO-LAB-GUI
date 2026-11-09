import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from PIL import Image


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        from yolo_backprop.workspaces.store import WorkspaceStore
        self.store = WorkspaceStore(self.root / 'settings' / 'workspaces.json')

    def test_new_workspace_lives_under_selected_parent_and_reopens_with_its_own_state(self):
        root = self.store.create(self.root, '缺陷检测')
        self.assertEqual(root, self.root / '缺陷检测')
        self.assertTrue((root / 'projects').is_dir())
        self.store.update(root, state={'training': {'epochs': 27}})
        second = self.store.create(self.root, '零件识别')
        self.assertEqual(self.store.read(second)['state'], {})
        self.assertEqual(self.store.read(root)['state']['training']['epochs'], 27)
        from yolo_backprop.workspaces.store import WorkspaceStore
        reopened = WorkspaceStore(self.store.path)
        self.assertEqual([v['root'] for v in reopened.recent()], [str(second), str(root)])

    def test_open_location_never_turns_an_existing_directory_into_a_project(self):
        location = self.root / '选中的目录'; location.mkdir()
        original = location / 'original.txt'; original.write_text('keep')
        with self.assertRaises(ValueError): self.store.open_location(location)
        self.assertEqual(original.read_text(), 'keep')
        self.assertEqual([p.name for p in location.iterdir()], ['original.txt'])
        self.assertEqual(self.store.recent(), [])

    def test_open_location_reuses_existing_workspace_without_creating_nested_folder(self):
        location = self.store.create(self.root, '已有项目')
        self.store.update(location, state={'training': {'epochs': 19}})
        self.assertEqual(self.store.open_location(location), location)
        self.assertEqual(self.store.read(location)['state']['training']['epochs'], 19)
        self.assertFalse((location / '新项目').exists())

    def test_read_existing_requires_a_valid_marker_and_does_not_write_or_register(self):
        from yolo_backprop.workspaces.store import MARKER
        root = self.store.create(self.root, '已存项目')
        marker = (root / MARKER).read_bytes(); history = self.store.path.read_bytes()
        info = self.store.read_existing(root)
        self.assertEqual(info['root'], str(root))
        self.assertEqual((root / MARKER).read_bytes(), marker)
        self.assertEqual(self.store.path.read_bytes(), history)
        lookalike = self.root / '不是项目'; (lookalike / 'projects').mkdir(parents=True)
        for read in (self.store.read_existing, self.store.open_location):
            with self.assertRaises(ValueError): read(lookalike)
        self.assertFalse((lookalike / MARKER).exists())
        self.assertEqual(self.store.path.read_bytes(), history)

    def test_open_location_does_not_replace_a_conflicting_user_file(self):
        location = self.root / '选中的目录'; location.mkdir()
        conflict = location / 'projects'; conflict.write_text('user file')
        with self.assertRaises((ValueError, OSError)): self.store.open_location(location)
        self.assertEqual(conflict.read_text(), 'user file')

    def test_invalid_names_and_existing_directories_do_not_overwrite_files(self):
        existing = self.root / 'existing'; existing.mkdir()
        (existing / 'user.txt').write_text('keep')
        for name in ('', '  ', '.', '..', '../escape', '/absolute', 'a/b', 'a\\b', 'existing',
                     'CON', 'NUL.txt', 'com1', '末尾.', '尾空格 ', '前\x01缀'):
            with self.subTest(name=name), self.assertRaises((ValueError, FileExistsError)):
                self.store.create(self.root, name)
        self.assertEqual((existing / 'user.txt').read_text(), 'keep')
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['existing'])

    def test_existing_workspace_is_adopted_without_changing_project_files(self):
        old = self.root / 'old'; project = old / 'projects' / 'existing'; project.mkdir(parents=True)
        original = project / 'original.json'; original.write_text('{"keep": true}')
        self.store.register(old)
        self.assertEqual(self.store.recent()[0]['root'], str(old))
        self.assertEqual(original.read_text(), '{"keep": true}')
        with self.assertRaises(ValueError): self.store.register(self.root)

    def test_old_remembered_workspace_remains_in_recent_list_after_first_new_workspace(self):
        from yolo_backprop.data_screening.workspace import WorkspaceSettings
        old = self.root / 'previous'
        WorkspaceSettings(self.store.path.with_name('workspace.json')).select(old)
        self.assertEqual(self.store.recent()[0]['root'], str(old))
        new = self.store.create(self.root, 'new')
        self.assertEqual([row['root'] for row in self.store.recent()], [str(new), str(old)])

    def test_missing_workspace_and_corrupt_history_do_not_break_home(self):
        root = self.store.create(self.root, 'offline')
        root.rename(self.root / 'moved')
        self.assertEqual(self.store.recent(), [])
        self.store.path.write_text('{broken')
        self.assertEqual(self.store.recent(), [])

    def test_removed_project_marker_hides_project_even_when_folder_and_projects_remain(self):
        from yolo_backprop.workspaces.store import MARKER
        root = self.store.create(self.root, '已删除记录')
        (root / MARKER).unlink()
        self.assertTrue((root / 'projects').is_dir())
        self.assertEqual(self.store.recent(), [])
        with self.assertRaises(ValueError): self.store.update(root, state={})
        self.assertFalse((root / MARKER).exists())

    def test_forget_clears_history_and_previous_selection_without_deleting_files(self):
        from yolo_backprop.data_screening.workspace import WorkspaceSettings
        root = self.store.create(self.root, '移除记录')
        settings = self.store.path.with_name('workspace.json')
        WorkspaceSettings(settings).select(root)
        self.store.forget(root)
        self.assertEqual(self.store.recent(), [])
        self.assertIsNone(WorkspaceSettings(settings).root)
        self.assertTrue(root.is_dir())

    def test_desktop_history_is_removed_without_touching_its_files_or_child_projects(self):
        from yolo_backprop.workspaces.store import MARKER
        from yolo_backprop.data_screening.workspace import WorkspaceSettings
        fake_home = self.root / 'home'; desktop = fake_home / '桌面'; desktop.mkdir(parents=True)
        original = desktop / '重要文件.txt'; original.write_text('must keep')
        (desktop / 'projects').mkdir()
        marker = desktop / MARKER
        marker.write_text(json.dumps({'version': 1, 'name': '桌面', 'state': {}}))
        marker_bytes = marker.read_bytes()
        child = self.store.create(desktop, '正常命名项目')
        self.store.path.write_text(json.dumps({'workspaces': [
            {'root': str(desktop), 'name': '桌面'}, {'root': str(child), 'name': '正常命名项目'}]}))
        WorkspaceSettings(self.store.path.with_name('workspace.json')).select(desktop)
        with patch('yolo_backprop.workspaces.store.Path.home', return_value=fake_home):
            self.assertEqual([row['root'] for row in self.store.recent()], [str(child)])
            self.store.prune_unsafe_locations()
            from yolo_backprop.workspaces.store import WorkspaceStore
            reopened = WorkspaceStore(self.store.path)
            self.assertEqual([row['root'] for row in reopened.recent()], [str(child)])
            self.assertIsNone(WorkspaceSettings(self.store.path.with_name('workspace.json')).root)
            with self.assertRaises(ValueError): self.store.register(desktop)
            with self.assertRaises(ValueError): self.store.register(fake_home)
            with self.assertRaises(ValueError): self.store.validate_deletion(desktop)
        self.assertEqual(original.read_text(), 'must keep')
        self.assertEqual(marker.read_bytes(), marker_bytes)
        self.assertTrue(child.is_dir())

    def test_forgetting_parent_only_removes_that_card_and_preserves_child(self):
        parent = self.store.create(self.root, '父项目')
        child = self.store.create(parent, '子项目')
        self.store.forget(parent)
        self.assertEqual([row['root'] for row in self.store.recent()], [str(child)])
        self.assertTrue(parent.is_dir()); self.assertTrue(child.is_dir())

    def test_only_newly_created_project_with_matching_ownership_can_be_deleted(self):
        from yolo_backprop.workspaces.store import MARKER, WorkspaceStore
        created = self.store.create(self.root, '新建项目')
        reopened = WorkspaceStore(self.store.path)
        self.assertEqual(reopened.validate_deletion(created)['root'], str(created))
        adopted = self.root / '已有目录'; (adopted / 'projects').mkdir(parents=True)
        self.store.register(adopted)
        with self.assertRaises(ValueError): self.store.validate_deletion(adopted)
        older = self.store.create(self.root, '旧版项目')
        document = json.loads((older / MARKER).read_text()); document.pop('ownership')
        (older / MARKER).write_text(json.dumps(document))
        self.store.register(older)
        with self.assertRaises(ValueError): self.store.validate_deletion(older)
        copied = self.root / '复制目录'; (copied / 'projects').mkdir(parents=True)
        (copied / MARKER).write_bytes((created / MARKER).read_bytes())
        with self.assertRaises(ValueError): self.store.validate_deletion(copied)
        link = self.root / '项目链接'; link.symlink_to(created, target_is_directory=True)
        with self.assertRaises(ValueError): self.store.validate_deletion(link)

    def test_recreated_directory_cannot_inherit_deletion_permission_from_a_copied_marker(self):
        from yolo_backprop.workspaces.store import MARKER
        created = self.store.create(self.root, '目录被替换')
        retired = self.root / '原目录'; created.rename(retired)
        (created / 'projects').mkdir(parents=True)
        (created / MARKER).write_bytes((retired / MARKER).read_bytes())
        original = created / '用户文件.txt'; original.write_text('keep')
        with self.assertRaises(ValueError): self.store.validate_deletion(created)
        self.assertEqual(original.read_text(), 'keep')

    def test_invalid_symlink_history_does_not_hide_the_real_project(self):
        created = self.store.create(self.root, '原项目')
        link = self.root / '符号链接'; link.symlink_to(created, target_is_directory=True)
        self.store.path.write_text(json.dumps({'workspaces': [
            {'root': str(link)}, {'root': str(created)}]}))
        self.assertEqual([row['root'] for row in self.store.recent()], [str(created)])

    def test_cover_is_cached_and_does_not_depend_on_original_image_remaining(self):
        root = self.store.create(self.root, 'photos')
        image = self.root / 'training.png'; Image.new('RGB', (1200, 800), 'red').save(image)
        original = image.read_bytes()
        self.store.set_cover(root, image, trained=True)
        self.assertEqual(image.read_bytes(), original)
        image.unlink()
        cover = Path(self.store.read(root)['cover'])
        self.assertTrue(cover.is_file())
        with Image.open(cover) as thumb: self.assertLessEqual(max(thumb.size), 640)
        self.assertTrue(self.store.read(root)['trained'])

    def test_training_cover_resolves_relative_dataset_and_txt_image_list(self):
        from yolo_backprop.workspaces.store import training_image
        dataset = self.root / 'dataset'; images = dataset / 'images' / 'train'; images.mkdir(parents=True)
        image = images / 'sample.png'; Image.new('RGB', (80, 60), 'blue').save(image)
        config = self.root / 'data.yaml'
        config.write_text('path: dataset\ntrain: images/train\n')
        self.assertEqual(training_image(config), image)
        (dataset / 'train.txt').write_text('./images/train/sample.png\n')
        config.write_text('path: dataset\ntrain: train.txt\n')
        self.assertEqual(training_image(config), image)
        config.write_text('train: missing\n')
        self.assertIsNone(training_image(config))

    def test_corrupt_workspace_metadata_is_reported_without_replacing_it(self):
        from yolo_backprop.workspaces.store import MARKER
        root = self.store.create(self.root, 'broken')
        marker = root / MARKER; marker.write_text('{broken')
        with self.assertRaises(ValueError): self.store.register(root)
        self.assertEqual(marker.read_text(), '{broken')
        self.assertEqual(self.store.recent(), [])
