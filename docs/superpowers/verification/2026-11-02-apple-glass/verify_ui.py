"""Capture the real native pages with isolated configuration and temporary data."""
import json
import os
from pathlib import Path
import sys
import tempfile

runtime = tempfile.TemporaryDirectory()
os.environ['XDG_DATA_HOME'] = runtime.name

from PyQt5 import QtCore, QtTest, QtWidgets
from tests.model_development.test_integration import IntegrationTests
from ISAT.workspaces.home import CreateProjectDialog

output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
output.mkdir(parents=True, exist_ok=True)
IntegrationTests.setUpClass()
fixture = IntegrationTests(); fixture.start_home = True; fixture.setUp()
geometry = {}

try:
    w = fixture.window; c = fixture.controller(); h = c.workspace_home
    base = Path(fixture.temp.name)
    h.store.forget(base / 'workspace')
    root = h.store.create(base, '零件检测')
    h.home.refresh(); w.resize(1440, 960)

    def capture(name):
        fixture.app.processEvents(); QtTest.QTest.qWait(80)
        assert w.grab().save(str(output / (name + '.png')))

    capture('home')
    dialog = CreateProjectDialog(base, h.home)
    def accept_name():
        dialog.activateWindow(); QtTest.QTest.qWaitForWindowActive(dialog, 1000)
        assert dialog.grab().save(str(output / 'create.png'))
        QtTest.QTest.keyClick(dialog.name_edit, QtCore.Qt.Key_Return)
        if dialog.isVisible(): dialog.reject()
    QtCore.QTimer.singleShot(150, accept_name)
    assert dialog.exec_() == dialog.Accepted
    dialog.deleteLater()
    assert h.open_workspace(root)
    page = c.screening_widget
    source = Path('tests/fixtures').resolve()
    page.open_folder(str(source)); fixture.wait_for_screening(page)
    page.grid.setCurrentRow(0); fixture.wait_for_screening(page)
    capture('screening')
    geometry['navigation'] = [c.navigation.x(), c.navigation.y(), c.navigation.width(), c.navigation.height()]
    geometry['screening'] = {name: [getattr(page, name).x(), getattr(page, name).y(),
                                  getattr(page, name).width(), getattr(page, name).height()]
                             for name in ('open_button', 'save_button',
                                          'import_button', 'splitter')}
    assert page.session.items
    QtTest.QTest.mouseClick(page.import_button, QtCore.Qt.LeftButton)
    fixture.wait_for_screening(page); fixture.app.processEvents()
    assert c.stack.currentWidget() is c.annotation_view and len(w.polygons) == 2
    capture('annotation')
    c.show_development(); fixture.app.processEvents()
    assert c.widget.train_tab._train_worker is None
    spin = c.widget.train_tab.tr_epochs
    old_value = spin.value()
    option = QtWidgets.QStyleOptionSpinBox(); spin.initStyleOption(option)
    up = spin.style().subControlRect(QtWidgets.QStyle.CC_SpinBox, option, QtWidgets.QStyle.SC_SpinBoxUp, spin)
    QtTest.QTest.mouseClick(spin, QtCore.Qt.LeftButton, pos=up.center())
    assert spin.value() == old_value + spin.singleStep()
    spin.setValue(old_value)
    c.widget.tabs.setCurrentIndex(2); fixture.app.processEvents()
    export = c.widget.export_tab
    QtTest.QTest.mouseClick(export._format_cards['engine'], QtCore.Qt.LeftButton)
    assert export._build_export_config().format == 'engine'
    QtTest.QTest.mouseClick(export._format_cards['onnx'], QtCore.Qt.LeftButton)
    assert export._build_export_config().format == 'onnx'
    for index, name in enumerate(('train', 'infer', 'export', 'logs', 'tools', 'settings')):
        c.widget.tabs.setCurrentIndex(index); capture(name)
    c.widget._change_theme()
    for index, name in enumerate(('train', 'infer', 'export', 'logs', 'tools', 'settings')):
        c.widget.tabs.setCurrentIndex(index); capture(name + '-dark')
    c.widget.tabs.setCurrentIndex(0)
    c.widget._change_theme()
    w.resize(1100, 760); capture('train-small')
    c.show_screening(); capture('screening-small')
    language = w.cfg['software']['language']
    w.cfg['software']['language'] = 'en'; c.retranslate(); fixture.app.processEvents()
    capture('navigation-en')
    for action in (c.home_action, c.screening_action, c.annotation_action, c.development_action):
        button = c.navigation.widgetForAction(action)
        assert button.width() >= button.fontMetrics().horizontalAdvance(action.text())
    w.cfg['software']['language'] = language; c.retranslate()
    h.show_home(); capture('home-small')
    (output / 'geometry.json').write_text(json.dumps(geometry, ensure_ascii=False, indent=2))
    print('PASS: home, Return naming, screening import, two native polygons, six model pages, dark toggle and small windows.', flush=True)
finally:
    fixture.doCleanups(); runtime.cleanup()
