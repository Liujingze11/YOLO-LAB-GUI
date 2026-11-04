"""Use native photo menus and the inline recovery strip with temporary copies."""
import os
from pathlib import Path
import shutil
import tempfile
import traceback

runtime = tempfile.TemporaryDirectory()
os.environ['XDG_DATA_HOME'] = runtime.name

from PyQt5 import QtCore, QtGui, QtTest, QtWidgets
from tests.model_development.test_integration import IntegrationTests

output = Path(__file__).resolve().parent
IntegrationTests.setUpClass()
fixture = IntegrationTests(); fixture.start_home = True; fixture.setUp()

try:
    w = fixture.window; c = fixture.controller(); h = c.workspace_home
    base = Path(fixture.temp.name)
    root = h.store.create(base, '图片筛选')
    assert h.open_workspace(root)
    page = c.screening_widget
    source = base / '原始照片'; source.mkdir()
    for n in range(6): shutil.copy2('tests/fixtures/sample.png', source / ('照片' + str(n + 1) + '.png'))
    original = {p.name: p.read_bytes() for p in source.iterdir()}
    page.open_folder(str(source)); fixture.wait_for_screening(page)
    w.resize(1440, 960); fixture.app.processEvents()
    assert not any(label.text().startswith('工作空间：') for label in page.findChildren(QtWidgets.QLabel))
    assert not any(button.text() in ('重命名', '移入回收站') for button in page.findChildren(QtWidgets.QPushButton))
    w.grab().save(str(output / 'empty-trash.png'))

    def photo_menu(key):
        page.grid.setFocus(); row = page.grid.item(0)
        QtTest.QTest.mouseClick(page.grid.viewport(), QtCore.Qt.LeftButton,
                               pos=page.grid.visualItemRect(row).center())
        errors = []
        def choose():
            menu = fixture.app.activePopupWidget()
            try:
                assert isinstance(menu, QtWidgets.QMenu)
                action = page.command_actions[key]
                assert action in menu.actions() and action.isEnabled()
                menu.grab().save(str(output / ('photo-menu-' + key + '.png')))
                QtTest.QTest.mouseClick(menu, QtCore.Qt.LeftButton,
                                       pos=menu.actionGeometry(action).center())
            except Exception as error:
                traceback.print_exc(); errors.append(error)
                if menu: menu.close()
        QtCore.QTimer.singleShot(100, choose)
        point = page.grid.visualItemRect(row).center()
        fixture.app.sendEvent(page.grid.viewport(), QtGui.QContextMenuEvent(
            QtGui.QContextMenuEvent.Mouse, point, page.grid.viewport().mapToGlobal(point)))
        assert not errors, errors

    def name_photo():
        dialog = fixture.app.activeModalWidget()
        assert isinstance(dialog, QtWidgets.QInputDialog)
        dialog.setTextValue('已重命名')
        QtCore.QMetaObject.invokeMethod(dialog, 'accept', QtCore.Qt.QueuedConnection)
    QtCore.QTimer.singleShot(180, name_photo)
    photo_menu('rename')
    assert page.grid.item(0).text() == '已重命名.png'
    for _ in range(4): photo_menu('remove')
    fixture.app.processEvents()
    assert page.trash_list.count() == 4 and page.grid.count() == 2
    assert len({page.trash_list.visualItemRect(page.trash_list.item(i)).y() for i in range(4)}) == 1
    w.grab().save(str(output / 'trash-filled.png'))

    def keep_trash():
        dialog = fixture.app.activeModalWidget()
        assert isinstance(dialog, QtWidgets.QMessageBox)
        button = next(button for button in dialog.buttons() if button.text() == '保留在回收站')
        QtTest.QTest.mouseClick(button, QtCore.Qt.LeftButton)
    QtCore.QTimer.singleShot(150, keep_trash)
    QtTest.QTest.mouseClick(page.save_button, QtCore.Qt.LeftButton)
    fixture.wait_for_screening(page)
    project = page.session.project_root
    page.open_folder(str(project), project=True); fixture.wait_for_screening(page)
    assert page.trash_list.count() == 4
    w.grab().save(str(output / 'trash-reopened.png'))
    strip = page.trash_list
    point = strip.visualItemRect(strip.item(0)).center()
    QtTest.QTest.mouseClick(strip.viewport(), QtCore.Qt.LeftButton, pos=point)
    QtTest.QTest.mouseDClick(strip.viewport(), QtCore.Qt.LeftButton, pos=point)
    fixture.wait_for_screening(page)
    assert strip.count() == 3 and page.grid.count() == 3
    w.resize(1100, 760); fixture.app.processEvents()
    w.grab().save(str(output / 'small-window.png'))
    strip.selectAll()
    QtTest.QTest.mouseClick(page.trash_restore_button, QtCore.Qt.LeftButton)
    fixture.wait_for_screening(page)
    assert strip.count() == 0 and page.grid.count() == 6
    assert {p.name: p.read_bytes() for p in source.iterdir()} == original
    print('PASS: native right-click rename/remove; four photos in one bottom row; saved/reopened thumbnails; double-click and multi-restore; original photos unchanged.', flush=True)
finally:
    fixture.doCleanups(); runtime.cleanup()
