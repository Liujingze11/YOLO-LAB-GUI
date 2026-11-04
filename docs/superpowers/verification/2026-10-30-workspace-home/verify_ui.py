"""Capture the native application with temporary workspaces and synthetic covers."""
from pathlib import Path

from PIL import Image, ImageDraw
from PyQt5 import QtCore, QtTest, QtWidgets

from tests.model_development.test_integration import IntegrationTests


output = Path(__file__).resolve().parent
IntegrationTests.setUpClass()
fixture = IntegrationTests(); fixture.start_home = True; fixture.setUp()
try:
    w = fixture.window; c = fixture.controller(); h = c.workspace_home
    w.setWindowTitle('YOLO-BACKPROP'); w.resize(1280, 860)
    fixture.app.processEvents(); fixture.app.processEvents()
    w.grab().save(str(output / 'startup.png'))
    roots = []
    for index, name in enumerate(('零件缺陷检测', '目标分割实验', '表面划痕识别')):
        root = h.store.create(Path(fixture.temp.name), name); roots.append(root)
        image = Image.new('RGB', (960, 640), ('#dfe7eb', '#263b40', '#e5ded4')[index])
        draw = ImageDraw.Draw(image)
        for row in range(2):
            for col in range(3):
                x, y = 110 + 270 * col, 100 + 250 * row
                draw.rounded_rectangle((x, y, x + 190, y + 180), radius=18,
                                       fill=('#869da6', '#73998f', '#a89a86')[index])
                draw.ellipse((x + 40, y + 35, x + 145, y + 140), fill=('#c7d4d9', '#bdd4c9', '#e3d5c0')[index])
        draw.rectangle((380, 90, 595, 295), outline='#e6b35a', width=6)
        image_path = Path(fixture.temp.name) / f'fixture-{index}.png'; image.save(image_path)
        h.store.set_cover(root, image_path, trained=True)
    h.home.refresh(); fixture.app.processEvents()
    w.grab().save(str(output / 'home.png'))
    for width, height in ((800, 650), (1500, 950)):
        w.resize(width, height); fixture.app.processEvents(); fixture.app.processEvents()
        print('home geometry', w.size().width(), w.size().height(), 'viewport', h.home.scroll.viewport().width())
        for card in h.home.cards:
            assert card.geometry().right() <= h.home.scroll.viewport().width()
        w.grab().save(str(output / f'home-{width}.png'))
    w.resize(1280, 860); fixture.app.processEvents()
    card = next(card for card in h.home.cards if card.info and card.info['root'] == str(roots[0]))
    QtTest.QTest.mouseClick(card, QtCore.Qt.LeftButton); fixture.app.processEvents()
    assert h.current_root == roots[0]
    w.grab().save(str(output / 'workbench.png'))
    c.show_development(); c.widget.train_tab.tr_epochs.setValue(29); fixture.app.processEvents()
    c.home_action.trigger(); fixture.app.processEvents()
    card = next(card for card in h.home.cards if card.info and card.info['root'] == str(roots[0]))
    QtTest.QTest.mouseClick(card, QtCore.Qt.LeftButton); fixture.app.processEvents()
    assert c.widget.train_tab.tr_epochs.value() == 29
    h.show_home(); fixture.app.processEvents()

    location = Path(fixture.temp.name) / '项目保存位置'; location.mkdir()
    project = location / '新的检测项目'
    def name_project():
        dialog = fixture.app.activeModalWidget()
        dialog.name_edit.setText(project.name)
        dialog.grab().save(str(output / 'create-workspace.png'))
        dialog.create_button.click()
    def select_location():
        dialog = fixture.app.activeModalWidget()
        assert isinstance(dialog, QtWidgets.QFileDialog)
        dialog.setDirectory(str(location))
        fixture.app.processEvents()
        dialog.grab().save(str(output / 'select-location.png'))
        QtCore.QMetaObject.invokeMethod(dialog, 'accept', QtCore.Qt.QueuedConnection)
        QtCore.QTimer.singleShot(100, name_project)
    timeout = QtCore.QTimer(); timeout.setSingleShot(True)
    timeout.timeout.connect(lambda: fixture.app.activeModalWidget().reject() if fixture.app.activeModalWidget() else None)
    timeout.start(5000)
    QtCore.QTimer.singleShot(100, select_location)
    QtTest.QTest.mouseClick(h.home.cards[0], QtCore.Qt.LeftButton)
    timeout.stop()
    fixture.app.processEvents()
    assert h.current_root == project
    assert c.stack.currentWidget() is c.screening_widget
    assert not h.home.isVisible()
    for action in (c.screening_action, c.annotation_action, c.development_action):
        assert c.navigation.widgetForAction(action).isVisible()
    w.grab().save(str(output / 'entered-workbench.png'))
    c.development_action.trigger(); fixture.app.processEvents()
    assert c.stack.currentWidget() is c.widget and c.widget.tabs.count() == 6
    w.grab().save(str(output / 'entered-model-development.png'))
    c.annotation_action.trigger(); fixture.app.processEvents()
    assert c.stack.currentWidget() is c.annotation_view and w.view.isVisible()
    c.screening_action.trigger(); fixture.app.processEvents()
    assert c.stack.currentWidget() is c.screening_widget
    print('PASS: native startup, responsive gallery, card opening, live form resume, real folder picker, project naming and workbench entry.')
finally:
    fixture.doCleanups()
