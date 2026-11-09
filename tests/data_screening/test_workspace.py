import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'original'; self.source.mkdir()
        for name in ('a.png', 'b.png'):
            Image.new('RGB', (40, 30), 'red').save(self.source / name)
        self.label = {'info': {'description': 'ISAT', 'width': 40, 'height': 30,
                               'name': 'a.png', 'folder': str(self.source)}, 'objects': []}
        (self.source / 'a.json').write_text(json.dumps(self.label))
        self.originals = {p.name: p.read_bytes() for p in self.source.iterdir()}
        from yolo_backprop.data_screening.workspace import Workspace
        self.workspace = Workspace(self.root / 'workspace')

    def assert_originals(self):
        self.assertEqual({p.name: p.read_bytes() for p in self.source.iterdir()}, self.originals)

    def test_import_copies_then_save_trash_reopen_restore_and_purge_only_copies(self):
        session = self.workspace.import_folder(self.source)
        a, b = session.items
        self.assertTrue(a.source.is_relative_to(self.workspace.root))
        self.assertNotEqual(a.source.stat().st_ino, (self.source / 'a.png').stat().st_ino)
        session.remove([a]); self.assertEqual(session.trash, [a])
        self.assertTrue(a.source.exists())
        result = session.save_project(categories=[])
        self.assertEqual(result['files'], ['b.png'])
        self.assertFalse((Path(result['image_root']) / 'a.png').exists())
        self.assertTrue(a.source.exists()); self.assertTrue(a.annotation.exists())
        reopened = self.workspace.open_project(session.project_root)
        self.assertEqual(len(reopened.trash), 1)
        reopened.restore(reopened.trash[:]); reopened.save_project()
        self.assertEqual(len(reopened.items), 2)
        a = next(i for i in reopened.items if i.name == 'a.png')
        reopened.remove([a]); reopened.save_project(); reopened.purge_trash()
        self.assertFalse(a.source.exists()); self.assertFalse(a.annotation.exists())
        self.assertEqual(self.workspace.open_project(reopened.project_root).trash, [])
        self.assert_originals()

    def test_rename_keeps_new_annotations_and_reserves_trash_names(self):
        session = self.workspace.import_folder(self.source)
        a, b = session.items
        session.remove([b])
        with self.assertRaises(ValueError): session.rename(a, 'b')
        self.label['objects'] = [{'category': 'new label'}]
        a.annotation.write_text(json.dumps(self.label))
        session.rename(a, 'renamed'); session.save_project()
        self.assertEqual(a.source.name, 'renamed.png')
        document = json.loads(a.annotation.read_text())
        self.assertEqual(document['objects'], self.label['objects'])
        self.assertEqual(document['info']['name'], 'renamed.png')
        self.assert_originals()

    def test_failed_save_rolls_back_and_does_not_allow_unsaved_purge(self):
        session = self.workspace.import_folder(self.source)
        a = session.items[0]; session.remove([a])
        with self.assertRaises(ValueError): session.purge_trash()
        from yolo_backprop.data_screening import workspace
        with patch.object(workspace, '_write_manifest', side_effect=OSError('disk full')):
            with self.assertRaises(OSError): session.save_project()
        reopened = self.workspace.open_project(session.project_root)
        self.assertEqual(len(reopened.items), 2); self.assertEqual(reopened.trash, [])
        self.assertTrue(a.source.exists()); self.assert_originals()

    def test_cancellation_leaves_no_partial_project_and_originals_unchanged(self):
        def cancelled(): raise RuntimeError('cancelled')
        with self.assertRaises(RuntimeError): self.workspace.import_folder(self.source, cancelled)
        self.assertEqual(list(self.workspace.projects()), [])
        self.assert_originals()

    def test_manifest_and_symlink_cannot_target_original_files_for_deletion(self):
        session = self.workspace.import_folder(self.source)
        a = session.items[0]; session.remove([a]); session.save_project()
        a.source.unlink(); a.source.symlink_to(self.source / 'a.png')
        with self.assertRaises(ValueError): session.purge_trash()
        self.assert_originals()
        marker = session.project_root / '.yolo-backprop-project.json'
        document = json.loads(marker.read_text()); document['entries'][0]['name'] = '../a.png'
        marker.write_text(json.dumps(document))
        with self.assertRaises(ValueError): self.workspace.open_project(session.project_root)

    def test_workspace_selection_is_persistent_and_does_not_need_existing_projects(self):
        from yolo_backprop.data_screening.workspace import WorkspaceSettings
        path = self.root / 'settings.json'
        store = WorkspaceSettings(path)
        store.select(self.workspace.root)
        self.assertEqual(WorkspaceSettings(path).root, self.workspace.root)
        self.assertEqual(list(self.workspace.projects()), [])

    def test_record_ids_cannot_be_paths_in_a_forged_manifest(self):
        session = self.workspace.import_folder(self.source)
        marker = session.project_root / '.yolo-backprop-project.json'
        document = json.loads(marker.read_text()); document['entries'][0]['id'] = '../escape'
        marker.write_text(json.dumps(document))
        with self.assertRaises(ValueError): self.workspace.open_project(session.project_root)

    def test_new_trash_destination_cannot_follow_an_external_directory_symlink(self):
        session = self.workspace.import_folder(self.source)
        (session.project_root / '.trash').symlink_to(self.source, target_is_directory=True)
        session.remove([session.items[0]])
        with self.assertRaises(ValueError): session.save_project(categories=[])
        self.assert_originals()
        self.assertEqual(len(self.workspace.open_project(session.project_root).items), 2)
