"""Capture the current native workbench using disposable projects/configuration."""
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

runtime = tempfile.TemporaryDirectory()
os.environ['XDG_DATA_HOME'] = runtime.name
os.environ['MPLCONFIGDIR'] = runtime.name

from PyQt5 import QtCore, QtTest, QtWidgets
from tests.model_development.test_integration import IntegrationTests

out = Path(__file__).resolve().parent
IntegrationTests.setUpClass()
fixture = IntegrationTests(); fixture.start_home = True; fixture.setUp()

try:
    w = fixture.window; c = fixture.controller(); h = c.workspace_home
    root = h.store.create(Path(fixture.temp.name), '零件检测')
    w.resize(1440, 960)

    def capture(name):
        fixture.app.processEvents(); QtTest.QTest.qWait(160)
        assert w.grab().save(str(out / (name + '.png')))

    capture('home')
    assert h.open_workspace(root)
    page = c.screening_widget
    page.open_folder(str(Path('tests/fixtures').resolve()))
    fixture.wait_for_screening(page)
    page.grid.setCurrentRow(0); fixture.wait_for_screening(page)
    capture('screening')
    with patch.object(page, '_confirm_purge', return_value=False):
        page.import_button.click(); fixture.wait_for_screening(page)
    assert c.stack.currentWidget() is c.annotation_view
    assert len(w.polygons) == 2
    assert c.frame.project.text() == '零件检测'
    capture('annotation')
    c.show_development(); fixture.app.processEvents()
    train = c.widget.train_tab
    capture('development')
    train.augmentation_card.set_expanded(True)
    capture('augmentation-expanded')
    train.augmentation_card.set_expanded(False)
    train._adv_toggle.setChecked(True)
    QtTest.QTest.qWait(200)
    assert train._adv_content.maximumHeight() > 0
    assert train._adv_content.height() > 0
    train._adv_toggle.setChecked(False)
    QtTest.QTest.qWait(200)
    for index, name in enumerate(('train', 'infer', 'export', 'logs', 'tools', 'settings')):
        c.widget.tabs.setCurrentIndex(index)
        if index: capture(name)
    c.widget.tabs.setCurrentIndex(0)
    c.widget._change_theme(); capture('development-dark')
    c.show_screening(); capture('screening-dark')
    c.show_annotation(); capture('annotation-dark')
    h.show_home(); capture('home-after-dark')
    assert h.open_workspace(root)
    c.show_development()
    assert c.widget._dark
    c.widget._change_theme()
    w.resize(1100, 760)
    for switch, name in ((c.show_development, 'development-small'),
                         (c.show_annotation, 'annotation-small'),
                         (c.show_screening, 'screening-small')):
        switch(); capture(name)
        assert c.frame.header.isVisible()
    c.show_development(); c.widget._language.setCurrentIndex(1)
    capture('development-english-small')
    c.widget._language.setCurrentIndex(0)
    c.show_screening()
    c.frame.project.setText('很长的项目名称用于验证窗口缩小后不会挤压标题和主要功能' * 5)
    capture('long-project')
    assert w.width() == 1100
    w.cfg['software']['language'] = 'en'; c.retranslate()
    capture('english')
    for action in (c.home_action, c.screening_action, c.annotation_action, c.development_action):
        button = c.navigation.widgetForAction(action)
        assert button.width() >= button.fontMetrics().horizontalAdvance(action.text())
    print('PASS: shared frame, actual screening/import/annotation, parameter folding, six model tabs, dark, small window and English.')
finally:
    fixture.doCleanups(); runtime.cleanup()
