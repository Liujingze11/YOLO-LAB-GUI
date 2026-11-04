"""Exercise native location/name dialogs and Return without touching real projects."""
import os
from pathlib import Path
import tempfile
import traceback

runtime = tempfile.TemporaryDirectory()
os.environ['XDG_DATA_HOME'] = runtime.name

from PyQt5 import QtCore, QtTest, QtWidgets
from ISAT.workspaces.home import CreateProjectDialog
from ISAT.workspaces.store import MARKER
from tests.model_development.test_integration import IntegrationTests


output = Path(__file__).resolve().parent
IntegrationTests.setUpClass()
fixture = IntegrationTests(); fixture.start_home = True; fixture.setUp()

try:
    w = fixture.window; c = fixture.controller(); h = c.workspace_home
    base = Path(fixture.temp.name)
    h.store.forget(base / 'workspace'); h.home.refresh()
    location = base / '项目保存位置'; location.mkdir()
    original = location / '原有文件.txt'; original.write_text('保留原文件', encoding='utf-8')
    w.resize(1280, 860); fixture.app.processEvents()

    def create(name, key, expected, image_name):
        h.show_home(); fixture.app.processEvents()
        errors = []

        def submit():
            dialog = fixture.app.activeModalWidget()
            try:
                assert isinstance(dialog, CreateProjectDialog)
                if name is not None: dialog.name_edit.setText(name)
                assert dialog.create_button.isEnabled()
                assert str(location / expected) in dialog.destination.text()
                dialog.activateWindow(); dialog.raise_()
                QtTest.QTest.qWaitForWindowActive(dialog, 1500)
                dialog.name_edit.setFocus()
                dialog.grab().save(str(output / image_name))
                if key is None: dialog.reject()
                else:
                    assert dialog.create_button.isDefault()
                    accepted = QtTest.QSignalSpy(dialog.accepted)
                    QtTest.QTest.keyClick(dialog.name_edit, key)
                    assert dialog.result() == dialog.Accepted
                    assert len(accepted) == 1
                    assert dialog.name_edit.text() == expected
            except Exception as error:
                traceback.print_exc()
                errors.append(error)
                if dialog: dialog.reject()

        def choose():
            dialog = fixture.app.activeModalWidget()
            try:
                assert isinstance(dialog, QtWidgets.QFileDialog)
                dialog.setDirectory(str(location))
                QtCore.QTimer.singleShot(150, submit)
                QtCore.QMetaObject.invokeMethod(dialog, 'accept', QtCore.Qt.QueuedConnection)
            except Exception as error:
                traceback.print_exc()
                errors.append(error)
                if dialog: dialog.reject()

        QtCore.QTimer.singleShot(150, choose)
        QtTest.QTest.mouseClick(h.home.cards[0], QtCore.Qt.LeftButton)
        fixture.app.processEvents()
        assert not errors, errors
        root = location / expected
        if key is None:
            assert not root.exists()
            return
        assert h.current_root == root and (root / MARKER).is_file()
        assert h.store.read(root)['name'] == expected
        assert c.stack.currentWidget() is c.screening_widget
        assert c.screening_widget.workspace.root == root
        assert c.navigation.isVisible() and not h.home.isVisible()
        assert not (location / MARKER).exists()
        assert original.read_text(encoding='utf-8') == '保留原文件'
        print('PASS: native dialogs + keyboard create and enter ' + expected, flush=True)

    create(None, QtCore.Qt.Key_Return, '新项目', 'default-name.png')
    kept = location / '新项目' / '原有数据.txt'; kept.write_text('不覆盖', encoding='utf-8')
    create('', QtCore.Qt.Key_Enter, '新项目 2', 'blank-name.png')
    w.grab().save(str(output / 'entered-workbench.png'))
    create('零件检测', QtCore.Qt.Key_Return, '零件检测', 'custom-name.png')
    before_cancel = set(location.iterdir())
    create(None, None, '新项目 3', 'cancel-name.png')
    assert set(location.iterdir()) == before_cancel
    assert kept.read_text(encoding='utf-8') == '不覆盖'
    assert {row['name'] for row in h.store.recent()} == {'新项目', '新项目 2', '零件检测'}
    w.grab().save(str(output / 'home.png'))
    assert w.close()
    assert original.read_text(encoding='utf-8') == '保留原文件'
    assert kept.read_text(encoding='utf-8') == '不覆盖'
    print('PASS: default names advance, cancellation creates nothing, parent and existing files remain untouched.', flush=True)
finally:
    fixture.doCleanups()
    runtime.cleanup()
