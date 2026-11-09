"""Render the real workbench using temporary settings and a temporary project."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from PyQt5 import QtCore, QtWidgets
from tests.model_development.test_integration import IntegrationTests

output = Path(__file__).parent
IntegrationTests.setUpClass()
fixture = IntegrationTests()
fixture.start_home = True
fixture.setUp()
try:
    window, app = fixture.window, fixture.app
    controller = fixture.controller()

    def capture(name):
        for _ in range(3): app.processEvents()
        assert window.grab().save(str(output / (name + '.png')))

    capture('01-home')
    root = controller.workspace_home.store.create(Path(fixture.temp.name), '你好')
    assert controller.workspace_home.open_workspace(root)
    capture('02-project')
    assert controller.title_bar.grab().save(str(output / 'title-bar.png'))
    controller.shortcut_button.click()
    app.processEvents()
    assert controller._shortcut_dialog.isVisible()
    assert controller._shortcut_dialog.grab().save(str(output / '03-shortcuts.png'))
    controller._shortcut_dialog.reject()
    controller.show_annotation()
    capture('04-annotation')
    controller.show_development()
    controller.widget.set_dark_mode(True)
    capture('05-dark')
    window.setWindowTitle('很长的中文项目名称' * 20 + ' · YOLO-BACKPROP')
    window.resize(980, 720)
    capture('06-long-title')
    assert controller.title_bar.title.toolTip() == window.windowTitle()
    assert controller.title_bar.title.text().endswith('…')
    print('Captured home, project, shortcuts, annotation, dark and long-title views.')
finally:
    fixture.doCleanups()
