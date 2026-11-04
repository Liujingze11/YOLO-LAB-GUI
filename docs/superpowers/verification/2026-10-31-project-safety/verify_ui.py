"""Exercise native project dialogs, uniform cards and deletion with disposable data."""
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

trash_runtime = tempfile.TemporaryDirectory()
os.environ['XDG_DATA_HOME'] = trash_runtime.name

from PyQt5 import QtCore, QtGui, QtTest, QtWidgets
from tests.model_development.test_integration import IntegrationTests
from ISAT.data_screening.workspace import WorkspaceSettings
from ISAT.workspaces.store import MARKER


output = Path(__file__).resolve().parent
IntegrationTests.setUpClass()
fixture = IntegrationTests(); fixture.start_home = True; fixture.setUp()
try:
    w = fixture.window; c = fixture.controller(); h = c.workspace_home
    test_root = Path(fixture.temp.name)
    h.store.forget(test_root / 'workspace')
    h.home.refresh()
    w.resize(1600, 860); fixture.app.processEvents()
    parent = test_root / '项目保存位置'; parent.mkdir()
    root = parent / '零件检测'

    def name_project():
        dialog = fixture.app.activeModalWidget()
        assert dialog is not None and hasattr(dialog, 'name_edit')
        assert dialog.name_edit.text() == '' and not dialog.create_button.isEnabled()
        dialog.grab().save(str(output / 'required-name.png'))
        QtTest.QTest.keyClick(dialog.name_edit, QtCore.Qt.Key_Return)
        assert dialog.isVisible() and not root.exists()
        dialog.name_edit.setText('   ')
        assert not dialog.create_button.isEnabled()
        dialog.name_edit.setText(root.name)
        assert dialog.create_button.isEnabled()
        dialog.grab().save(str(output / 'project-name.png'))
        dialog.create_button.click()

    def select_location():
        dialog = fixture.app.activeModalWidget()
        assert isinstance(dialog, QtWidgets.QFileDialog)
        dialog.setDirectory(str(parent))
        QtCore.QMetaObject.invokeMethod(dialog, 'accept', QtCore.Qt.QueuedConnection)
        QtCore.QTimer.singleShot(100, name_project)

    QtCore.QTimer.singleShot(100, select_location)
    QtTest.QTest.mouseClick(h.home.cards[0], QtCore.Qt.LeftButton)
    fixture.app.processEvents()
    assert h.current_root == root and root.is_dir()
    assert c.stack.currentWidget() is c.screening_widget and c.navigation.isVisible()
    assert not (parent / MARKER).exists() and not (parent / 'projects').exists()
    print('PASS: empty name and Return cannot create; named child enters workbench; parent untouched.', flush=True)

    second = h.store.create(parent, '划痕识别')
    h.store.set_cover(root, Path('tests/fixtures/sample.png').resolve())
    h.show_home(); fixture.app.processEvents()
    for width in (1600, 800, 1180, 1600):
        w.resize(width, 860); fixture.app.processEvents(); fixture.app.processEvents()
        assert all(card.size() == QtCore.QSize(300, 284) for card in h.home.cards)
        assert all(card.geometry().right() <= h.home.scroll.viewport().width() for card in h.home.cards)
        w.grab().save(str(output / ('home-' + str(width) + '.png')))
    print('PASS: all cards 300 x 284 at 800, 1180 and 1600 pixels, including repeated resize.', flush=True)

    desktop = test_root / '桌面'; (desktop / 'projects').mkdir(parents=True)
    original = desktop / '重要文件.txt'; original.write_text('never move or delete')
    marker = desktop / MARKER
    marker.write_text(json.dumps({'version': 1, 'name': '桌面', 'state': {}}))
    original_bytes = marker.read_bytes()
    history = json.loads(h.store.path.read_text())
    history['workspaces'].insert(0, {'root': str(desktop), 'name': '桌面'})
    h.store.path.write_text(json.dumps(history))
    WorkspaceSettings(h.store.path.with_name('workspace.json')).select(desktop)
    standard_locations = QtCore.QStandardPaths.standardLocations
    def temporary_desktop(kind):
        return [str(desktop)] if kind == QtCore.QStandardPaths.DesktopLocation else standard_locations(kind)
    with patch.object(QtCore.QStandardPaths, 'standardLocations', temporary_desktop):
        h.store.prune_unsafe_locations(); h.home.refresh()
        assert all(not card.info or card.info['root'] != str(desktop) for card in h.home.cards)
        try: h.store.validate_deletion(desktop)
        except ValueError: pass
        else: raise AssertionError('desktop deletion was allowed')
    assert original.read_text() == 'never move or delete' and marker.read_bytes() == original_bytes
    assert (desktop / 'projects').is_dir() and second.is_dir()
    print('PASS: old desktop selection removed from configuration; files and marker untouched.', flush=True)

    adopted = test_root / '旧版目录'; (adopted / 'projects').mkdir(parents=True)
    kept = adopted / '原有文件.txt'; kept.write_text('keep')
    h.store.register(adopted); h.home.refresh(); fixture.app.processEvents()
    card = next(card for card in h.home.cards if card.info and card.info['root'] == str(adopted))

    def remove_card():
        menu = fixture.app.activePopupWidget(); assert isinstance(menu, QtWidgets.QMenu)
        actions = {action.objectName(): action for action in menu.actions()}
        assert not actions['delete'].isEnabled() and actions['remove'].isEnabled()
        menu.grab().save(str(output / 'legacy-menu.png'))
        QtTest.QTest.mouseClick(menu, QtCore.Qt.LeftButton, pos=menu.actionGeometry(actions['remove']).center())

    QtCore.QTimer.singleShot(100, remove_card)
    event = QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Mouse, card.rect().center(),
                                   card.mapToGlobal(card.rect().center()))
    fixture.app.sendEvent(card, event)
    fixture.app.processEvents()
    assert kept.read_text() == 'keep' and adopted.is_dir()
    assert str(adopted) not in [row['root'] for row in h.store.recent()]
    w.grab().save(str(output / 'home.png'))
    print('PASS: real legacy right-click menu disables deletion; remove keeps original files.', flush=True)

    def confirm_delete():
        dialog = fixture.app.activeModalWidget(); assert isinstance(dialog, QtWidgets.QMessageBox)
        dialog.grab().save(str(output / 'delete-confirmation.png'))
        dialog.button(QtWidgets.QMessageBox.Yes).click()

    QtCore.QTimer.singleShot(100, confirm_delete)
    assert h.delete_workspace(str(root))
    assert not root.exists() and h.current_root is None and second.is_dir()
    assert list(Path(trash_runtime.name).rglob(MARKER))
    assert w.close() and not root.exists()
    assert kept.read_text() == 'keep' and original.read_text() == 'never move or delete'
    print('PASS: actual system trash only moves the created named project; exit does not recreate it.', flush=True)
finally:
    fixture.doCleanups()
    trash_runtime.cleanup()
