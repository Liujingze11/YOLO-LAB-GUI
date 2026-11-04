"""Verify actual native dialogs and system trash using disposable project data."""
import os
from pathlib import Path
import shutil
import tempfile

trash_runtime = tempfile.TemporaryDirectory()
os.environ['XDG_DATA_HOME'] = trash_runtime.name

from PyQt5 import QtCore, QtGui, QtTest, QtWidgets
from tests.model_development.test_integration import IntegrationTests
from ISAT.workspaces.store import MARKER


output = Path(__file__).resolve().parent
IntegrationTests.setUpClass()
fixture = IntegrationTests(); fixture.start_home = True; fixture.setUp()
try:
    w = fixture.window; c = fixture.controller(); h = c.workspace_home
    w.resize(1280, 860); fixture.app.processEvents()
    parent = Path(fixture.temp.name) / '项目保存位置'; parent.mkdir()
    root = parent / '零件检测'

    def name_project():
        dialog = fixture.app.activeModalWidget()
        assert dialog is not None and hasattr(dialog, 'name_edit')
        dialog.name_edit.setText(root.name)
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
    assert c.stack.currentWidget() is c.screening_widget
    assert c.navigation.isVisible()
    w.grab().save(str(output / 'created-workbench.png'))
    print('PASS: select location, name project, matching folder, automatic workbench entry.', flush=True)

    h.store.set_cover(root, Path('tests/fixtures/sample.png').resolve())
    h.show_home(); fixture.app.processEvents()
    w.grab().save(str(output / 'home.png'))
    card = next(card for card in h.home.cards if card.info and card.info['root'] == str(root))

    def choose_copy():
        menu = fixture.app.activePopupWidget()
        assert isinstance(menu, QtWidgets.QMenu)
        menu.grab().save(str(output / 'context-menu.png'))
        action = next(action for action in menu.actions() if action.objectName() == 'copy_path')
        QtTest.QTest.mouseClick(menu, QtCore.Qt.LeftButton, pos=menu.actionGeometry(action).center())

    QtCore.QTimer.singleShot(100, choose_copy)
    event = QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Mouse, card.rect().center(),
                                   card.mapToGlobal(card.rect().center()))
    fixture.app.sendEvent(card, event)
    assert fixture.app.clipboard().text() == str(root)
    print('PASS: actual right-click menu and copy-path command.', flush=True)

    def confirm_delete():
        dialog = fixture.app.activeModalWidget()
        assert isinstance(dialog, QtWidgets.QMessageBox)
        dialog.grab().save(str(output / 'delete-confirmation.png'))
        dialog.button(QtWidgets.QMessageBox.Yes).click()

    QtCore.QTimer.singleShot(100, confirm_delete)
    assert h.delete_workspace(str(root))
    fixture.app.processEvents()
    assert not root.exists() and h.current_root is None
    assert list(Path(trash_runtime.name).rglob(MARKER)), 'project is recoverable in isolated system trash'
    assert w.close() and not root.exists()
    print('PASS: actual QFile.moveToTrash, active project cleared, exit does not recreate folder.', flush=True)

    removed = h.store.create(parent, '外部删除验证')
    h.home.refresh()
    shutil.rmtree(removed)
    h.home.refresh()
    assert all(not card.info or card.info['root'] != str(removed) for card in h.home.cards)
    print('PASS: externally deleted project no longer appears.', flush=True)
finally:
    fixture.doCleanups()
    trash_runtime.cleanup()
