"""Open minimal image, ISAT and YOLO sources through native UI; never change sources."""
import os
from pathlib import Path
import shutil
import tempfile

runtime = tempfile.TemporaryDirectory()
os.environ['XDG_DATA_HOME'] = runtime.name

from PIL import Image
from PyQt5 import QtCore, QtGui, QtTest, QtWidgets
from tests.model_development.test_integration import IntegrationTests


output = Path(__file__).resolve().parent
IntegrationTests.setUpClass()
fixture = IntegrationTests(); fixture.start_home = True; fixture.setUp()


def snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes() if path.is_file() else None
            for path in root.rglob('*')}


try:
    w = fixture.window; c = fixture.controller(); h = c.workspace_home
    base = Path(fixture.temp.name)
    h.store.forget(base / 'workspace'); h.home.refresh()
    w.resize(1280, 860); fixture.app.processEvents()
    plain = base / '只有图片'; plain.mkdir()
    Image.new('RGB', (320, 240), '#4a9885').save(plain / 'photo.png')
    isat = base / '已有ISAT标注'; (isat / 'images').mkdir(parents=True); (isat / 'json').mkdir()
    shutil.copy2('tests/fixtures/sample.png', isat / 'images' / 'sample.png')
    shutil.copy2('tests/fixtures/sample.json', isat / 'json' / 'sample.json')
    yolo = base / 'YOLO数据集'; (yolo / 'images' / 'train').mkdir(parents=True)
    (yolo / 'images' / 'val').mkdir(); (yolo / 'labels' / 'train').mkdir(parents=True)
    Image.new('RGB', (80, 60), 'red').save(yolo / 'images' / 'train' / 'part.png')
    Image.new('RGB', (80, 60), 'blue').save(yolo / 'images' / 'val' / 'part.png')
    (yolo / 'labels' / 'train' / 'part.txt').write_text('0 0.1 0.1 0.8 0.1 0.8 0.8 0.1 0.8\n')
    (yolo / 'data.yaml').write_text('train: images/train\nval: images/val\nnames: [part]\n')
    originals = {root: snapshot(root) for root in (plain, isat, yolo)}

    def select(root):
        h.show_home(); fixture.app.processEvents()
        def choose():
            dialog = fixture.app.activeModalWidget()
            assert isinstance(dialog, QtWidgets.QFileDialog)
            dialog.setDirectory(str(root))
            dialog.grab().save(str(output / ('choose-' + root.name + '.png')))
            QtCore.QMetaObject.invokeMethod(dialog, 'accept', QtCore.Qt.QueuedConnection)
        QtCore.QTimer.singleShot(100, choose)
        QtTest.QTest.mouseClick(h.home.cards[1], QtCore.Qt.LeftButton)
        fixture.app.processEvents()
        assert h.current_root == root

    select(plain)
    page = c.screening_widget; fixture.wait_for_screening(page)
    assert len(page.session.items) == 1 and page.session.project_root.is_relative_to(h.storage_root)
    assert not (page.session.project_root / 'json' / 'photo.json').exists()
    assert str(h.storage_root) not in page.source_label.text()
    w.grab().save(str(output / 'images-only.png'))
    print('PASS: a folder containing only one image opens in screening; no annotation or structure is required.', flush=True)

    select(isat)
    page = c.screening_widget; fixture.wait_for_screening(page)
    QtTest.QTest.mouseClick(page.import_button, QtCore.Qt.LeftButton)
    fixture.wait_for_screening(page); fixture.app.processEvents()
    assert c.stack.currentWidget() is c.annotation_view and len(w.polygons) == 2
    w.grab().save(str(output / 'isat-annotation.png'))
    print('PASS: real ISAT images/json source opens; import button restores both polygons on native canvas.', flush=True)

    select(yolo)
    assert c.stack.currentWidget() is c.widget
    assert c.widget.train_tab.tr_data_yaml.currentText() == str(yolo / 'data.yaml')
    assert c.widget.train_tab._train_worker is None
    assert not Path(c.widget.train_tab.tr_results.currentText()).is_relative_to(yolo)
    w.grab().save(str(output / 'yolo-development.png'))
    print('PASS: YOLO dataset automatically fills its original data.yaml and opens development without starting training.', flush=True)

    h.show_home(); fixture.app.processEvents()
    assert {row['root'] for row in h.store.recent()} == {str(root) for root in originals}
    w.grab().save(str(output / 'home.png'))
    card = next(card for card in h.home.cards if card.info and card.info['root'] == str(plain))
    def copy_path():
        menu = fixture.app.activePopupWidget(); assert isinstance(menu, QtWidgets.QMenu)
        actions = {action.objectName(): action for action in menu.actions()}
        assert not actions['delete'].isEnabled() and actions['remove'].isEnabled()
        menu.grab().save(str(output / 'external-menu.png'))
        QtTest.QTest.mouseClick(menu, QtCore.Qt.LeftButton, pos=menu.actionGeometry(actions['copy_path']).center())
    QtCore.QTimer.singleShot(100, copy_path)
    fixture.app.sendEvent(card, QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Mouse, card.rect().center(),
                                                     card.mapToGlobal(card.rect().center())))
    assert fixture.app.clipboard().text() == str(plain)
    assert w.close()
    for root, before in originals.items(): assert snapshot(root) == before
    print('PASS: external recent paths point to original sources; deletion disabled; all source files/directories unchanged through exit.', flush=True)
finally:
    fixture.doCleanups()
    runtime.cleanup()
