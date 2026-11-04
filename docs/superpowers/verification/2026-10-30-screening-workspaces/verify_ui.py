"""Capture the actual native app with synthetic images and isolated user settings."""
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw
from PyQt5 import QtCore, QtGui, QtWidgets
from tests.model_development.test_integration import IntegrationTests
from ISAT.data_screening.dialogs import WorkspaceDialog


output = Path(__file__).resolve().parent
IntegrationTests.setUpClass()
fixture = IntegrationTests()
fixture.setUp()
try:
    source = Path(fixture.temp.name) / 'demo-images'; source.mkdir()
    for index in range(12):
        image = Image.new('RGB', (960, 640), '#f1f1ee')
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 420, 960, 640), fill='#d5d6d0')
        x = 200 + index * 27
        draw.rounded_rectangle((x, 200, x + 240, 440), radius=15, fill=['#476478', '#887868', '#607361'][index % 3])
        draw.ellipse((x + 30, 240, x + 200, 410), fill='#e7e5d8')
        draw.text((40, 40), 'FRAME %02d - SCREENING FIXTURE' % (index + 1), fill='black')
        image.save(source / ('frame-%02d.png' % (index + 1)))
    window = fixture.window; controller = fixture.controller()
    window.resize(1500, 950); controller.show_screening()
    page = controller.screening_widget
    page.open_folder(str(source)); fixture.wait_for_screening(page)
    page.grid.setCurrentRow(11); page.command_actions['remove'].trigger()
    with patch.object(page, '_confirm_purge', return_value=False):
        page.save_screening(); fixture.wait_for_screening(page)
    page.grid.setCurrentRow(0)
    page.compare_with(str(page.session.items[3].source)); fixture.wait_for_screening(page)
    fixture.app.processEvents()
    window.grab().save(str(output / 'workspace-comparison.png'))
    trash = page.create_trash_dialog(); trash.show(); fixture.app.processEvents()
    trash.grab().save(str(output / 'trash.png')); trash.close()
    workspace = WorkspaceDialog(page); workspace.show(); fixture.app.processEvents()
    workspace.grab().save(str(output / 'workspace-picker.png')); workspace.close()
    page.exit_comparison(); fixture.app.processEvents()
    mime = page.grid.mimeData([page.grid.item(2)])
    event = QtGui.QDragEnterEvent(QtCore.QPoint(page.preview.viewport().width() - 20, 50),
        QtCore.Qt.CopyAction, mime, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
    fixture.app.sendEvent(page.preview.viewport(), event); fixture.app.processEvents()
    window.grab().save(str(output / 'drop-hint.png'))
    fixture.app.sendEvent(page.preview.viewport(), QtGui.QDragLeaveEvent())

    def capture_confirmation():
        dialog = fixture.app.activeModalWidget()
        dialog.grab().save(str(output / 'delete-confirmation.png'))
        dialog.defaultButton().click()
    QtCore.QTimer.singleShot(100, capture_confirmation)
    assert page._confirm_purge() is False
    print('Captured native workspace, comparison, drop hint, trash and delete confirmation.')
finally:
    fixture.doCleanups()
