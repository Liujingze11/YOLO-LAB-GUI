"""Use the real open-project card and directory picker with disposable projects."""
import os
from pathlib import Path
import tempfile

runtime = tempfile.TemporaryDirectory()
os.environ['XDG_DATA_HOME'] = runtime.name

from PyQt5 import QtCore, QtTest, QtWidgets
from tests.model_development.test_integration import IntegrationTests
from ISAT.workspaces.store import WorkspaceStore


output = Path(__file__).resolve().parent
IntegrationTests.setUpClass()
fixture = IntegrationTests(); fixture.start_home = True; fixture.setUp()
try:
    w = fixture.window; c = fixture.controller(); h = c.workspace_home
    test_root = Path(fixture.temp.name)
    h.store.forget(test_root / 'workspace'); h.home.refresh()
    w.resize(1280, 860); fixture.app.processEvents()
    assert [card.accessibleName() for card in h.home.cards] == ['新建项目', '打开项目']
    assert all(card.size() == QtCore.QSize(300, 284) for card in h.home.cards)
    w.grab().save(str(output / 'empty-home.png'))

    other = WorkspaceStore(test_root / 'other-config' / 'workspaces.json')
    root = other.create(test_root, '零件检测')
    other.update(root, state={'page': 'development', 'training': {'epochs': 37}})
    other.set_cover(root, Path('tests/fixtures/sample.png').resolve())
    original = root / '原数据.txt'; original.write_text('keep')

    def select_existing():
        dialog = fixture.app.activeModalWidget()
        assert isinstance(dialog, QtWidgets.QFileDialog)
        dialog.setDirectory(str(root))
        dialog.grab().save(str(output / 'select-project.png'))
        QtCore.QMetaObject.invokeMethod(dialog, 'accept', QtCore.Qt.QueuedConnection)

    QtCore.QTimer.singleShot(100, select_existing)
    QtTest.QTest.mouseClick(h.home.cards[1], QtCore.Qt.LeftButton)
    fixture.app.processEvents()
    assert h.current_root == root and c.stack.currentWidget() is c.widget
    assert c.widget.train_tab.tr_epochs.value() == 37 and c.navigation.isVisible()
    assert original.read_text() == 'keep' and not (root / root.name).exists()
    w.grab().save(str(output / 'restored-workbench.png'))
    print('PASS: actual open card and directory picker enter existing workbench and restore 37 epochs.', flush=True)

    h.show_home(); fixture.app.processEvents()
    for width in (800, 1280, 1600):
        w.resize(width, 860); fixture.app.processEvents(); fixture.app.processEvents()
        assert all(card.size() == QtCore.QSize(300, 284) for card in h.home.cards)
        assert all(card.geometry().right() <= h.home.scroll.viewport().width() for card in h.home.cards)
        w.grab().save(str(output / ('home-' + str(width) + '.png')))
    assert [row['root'] for row in h.store.recent()].count(str(root)) == 1
    print('PASS: new/open/recent cards stay equal at 800, 1280, 1600 pixels; recent entry registered once.', flush=True)

    def cancel_picker():
        dialog = fixture.app.activeModalWidget()
        assert isinstance(dialog, QtWidgets.QFileDialog)
        dialog.reject()

    history = h.store.path.read_bytes()
    QtCore.QTimer.singleShot(100, cancel_picker)
    QtTest.QTest.mouseClick(h.home.cards[1], QtCore.Qt.LeftButton)
    assert h.store.path.read_bytes() == history and h.current_root == root
    print('PASS: cancelling the real directory picker leaves files, history and current project unchanged.', flush=True)

    plain = test_root / '普通图片文件夹'; plain.mkdir()
    kept = plain / '用户文件.txt'; kept.write_text('keep')

    def close_invalid():
        dialog = fixture.app.activeModalWidget()
        assert isinstance(dialog, QtWidgets.QMessageBox)
        dialog.grab().save(str(output / 'invalid-project.png'))
        dialog.button(QtWidgets.QMessageBox.Ok).click()

    def select_plain():
        dialog = fixture.app.activeModalWidget()
        assert isinstance(dialog, QtWidgets.QFileDialog)
        dialog.setDirectory(str(plain))
        QtCore.QMetaObject.invokeMethod(dialog, 'accept', QtCore.Qt.QueuedConnection)
        QtCore.QTimer.singleShot(100, close_invalid)

    QtCore.QTimer.singleShot(100, select_plain)
    QtTest.QTest.mouseClick(h.home.cards[1], QtCore.Qt.LeftButton)
    assert h.current_root == root and c.stack.currentWidget() is h.home
    assert h.store.path.read_bytes() == history and list(plain.iterdir()) == [kept]
    assert kept.read_text() == 'keep'
    print('PASS: actual invalid-folder dialog refuses ordinary directories without creating or registering a project.', flush=True)
finally:
    fixture.doCleanups()
    runtime.cleanup()
