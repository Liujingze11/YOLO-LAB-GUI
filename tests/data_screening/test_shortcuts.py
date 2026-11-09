from pathlib import Path
import tempfile
import unittest


class ShortcutSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'config/shortcuts.json'

    def settings(self):
        from yolo_backprop.data_screening.shortcuts import ShortcutSettings
        return ShortcutSettings(self.path)

    def test_saved_bindings_reload_and_empty_binding_disables_shortcut(self):
        settings = self.settings()
        settings.save({'rename': 'Ctrl+R', 'remove': ''})
        reloaded = self.settings()
        self.assertEqual(reloaded.bindings['rename'], 'Ctrl+R')
        self.assertEqual(reloaded.bindings['remove'], '')
        self.assertEqual(reloaded.bindings['next'], 'Right')

    def test_conflicting_or_multistep_bindings_never_replace_previous_file(self):
        settings = self.settings(); settings.save({'rename': 'Ctrl+R'})
        original = self.path.read_bytes()
        for invalid in ({'rename': 'Delete'}, {'rename': 'Ctrl+K, Ctrl+R'}, {'unknown': 'F8'}, {'rename': 'NotAKey'}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError): settings.save(invalid)
            self.assertEqual(self.path.read_bytes(), original)
            self.assertEqual(settings.bindings['rename'], 'Ctrl+R')

    def test_broken_file_falls_back_without_overwriting_user_data(self):
        self.path.parent.mkdir(); self.path.write_text('{broken')
        settings = self.settings()
        self.assertEqual(settings.bindings['rename'], 'F2')
        self.assertEqual(self.path.read_text(), '{broken')
