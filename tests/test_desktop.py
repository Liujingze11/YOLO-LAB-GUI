import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from yolo_backprop import desktop


class DesktopLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'moved checkout'
        package = self.root / 'yolo_backprop'
        package.mkdir(parents=True)
        (self.root / 'run-yolo-backprop.sh').write_text('#!/bin/sh\nexit 0\n')
        (self.root / 'run-yolo-backprop.sh').chmod(0o755)
        (package / 'yolo-backprop-transparent.svg').write_text('<svg/>')
        for mock in (
            patch.object(desktop, '__file__', str(package / 'desktop.py')),
            patch.dict(os.environ, {'XDG_DATA_HOME': str(self.base / 'share'),
                                    'XDG_STATE_HOME': str(self.base / 'state')}),
            patch.object(desktop.shutil, 'which', return_value=None),
        ):
            mock.start()
            self.addCleanup(mock.stop)
        self.apps = self.base / 'share/applications'
        self.apps.mkdir(parents=True)

    def test_replaces_cached_legacy_identity_and_preserves_its_backup(self):
        legacy = self.apps / 'ISAT.desktop'
        previous = ('[Desktop Entry]\nName=YOLO-BACKPROP\n'
                    'Exec=/removed/checkout/run-isat.sh\nPath=/removed/checkout\n')
        legacy.write_text(previous)

        installed = desktop.install_launcher()

        self.assertNotEqual(installed.name, legacy.name)
        self.assertFalse(legacy.exists())
        self.assertTrue(installed.is_file())
        self.assertTrue(os.access(installed, os.X_OK))
        entry = installed.read_text()
        self.assertNotIn('/removed/checkout', entry)
        self.assertIn(str(self.root / 'run-yolo-backprop.sh'), entry)
        backups = list((self.base / 'state/yolo-backprop/launcher-backups').glob('*.desktop'))
        self.assertTrue(any(path.read_text() == previous for path in backups))

        self.assertEqual(desktop.install_launcher(), installed)
        self.assertEqual(list(self.apps.glob('*.desktop')), [installed])

    def test_retains_an_unrelated_original_isat_launcher(self):
        legacy = self.apps / 'ISAT.desktop'
        previous = '[Desktop Entry]\nName=ISAT\nExec=/opt/isat/start\n'
        legacy.write_text(previous)

        installed = desktop.install_launcher()

        self.assertEqual(legacy.read_text(), previous)
        self.assertNotEqual(installed, legacy)
