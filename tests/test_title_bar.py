"""Window chrome contracts, exercised with real Qt widgets and events."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from unittest.mock import patch

from PyQt5 import QtCore, QtGui, QtTest, QtWidgets


class GuardedWindow(QtWidgets.QMainWindow):
    allow_close = False
    close_requests = 0

    def closeEvent(self, event):
        self.close_requests += 1
        event.setAccepted(self.allow_close)


class TitleBarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        from yolo_backprop.title_bar import WorkbenchTitleBar
        self.window = GuardedWindow()
        self.window.setObjectName('MainWindow')
        self.window.setMinimumSize(360, 240)
        self.window.setCentralWidget(QtWidgets.QWidget())
        self.bar = WorkbenchTitleBar(self.window)
        self.window.setMenuWidget(self.bar)
        self.window.setGeometry(100, 100, 800, 500)
        self.window.show()
        self.app.processEvents()
        self.addCleanup(self.window.deleteLater)
        self.addCleanup(self.window.hide)

    def mouse(self, widget, kind, global_pos, button=QtCore.Qt.NoButton, buttons=QtCore.Qt.LeftButton):
        local = widget.mapFromGlobal(global_pos)
        event = QtGui.QMouseEvent(kind, QtCore.QPointF(local), QtCore.QPointF(global_pos),
                                 button, buttons, QtCore.Qt.NoModifier)
        self.app.sendEvent(widget, event)
        self.app.processEvents()

    def test_title_and_buttons_share_one_row_and_long_names_do_not_cover_controls(self):
        self.window.setWindowTitle('你好 · YOLO-BACKPROP')
        self.app.processEvents()
        self.assertTrue(self.window.windowFlags() & QtCore.Qt.FramelessWindowHint)
        self.assertEqual(self.bar.title.text(), '你好 · YOLO-BACKPROP')
        for button in (self.bar.shortcut_button, self.bar.minimize_button,
                       self.bar.maximize_button, self.bar.close_button):
            self.assertLessEqual(abs(button.geometry().center().y() - self.bar.title.geometry().center().y()), 1)
            self.assertFalse(button.geometry().intersects(self.bar.title.geometry()))
        self.assertLessEqual(abs(self.bar.title.geometry().center().x() - self.bar.rect().center().x()), 1)
        name = '<项目>很长的中文项目名称' * 30
        self.window.setWindowTitle(name)
        self.window.resize(400, 300)
        self.app.processEvents()
        self.assertNotEqual(self.bar.title.text(), name)
        self.assertIn('…', self.bar.title.text())
        self.assertEqual(self.bar.title.toolTip(), name)
        self.assertLessEqual(self.bar.title.fontMetrics().horizontalAdvance(self.bar.title.text()), self.bar.title.width())
        position = self.bar.title.geometry().center()
        target = self.window.childAt(self.bar.mapTo(self.window, position))
        local = target.mapFromGlobal(self.bar.mapToGlobal(position))
        help_event = QtGui.QHelpEvent(QtCore.QEvent.ToolTip, local, target.mapToGlobal(local))
        self.app.sendEvent(target, help_event)
        self.addCleanup(QtWidgets.QToolTip.hideText)
        self.assertEqual(QtWidgets.QToolTip.text(), name, 'hovering the elided title reveals the full name')

    def test_window_buttons_double_click_and_close_guard(self):
        self.bar.maximize_button.click()
        self.app.processEvents()
        self.assertTrue(self.window.isMaximized())
        self.assertIn('还原', self.bar.maximize_button.toolTip())
        QtTest.QTest.mouseDClick(self.bar, QtCore.Qt.LeftButton, pos=self.bar.rect().center())
        self.app.processEvents()
        self.assertFalse(self.window.isMaximized())
        self.bar.minimize_button.click()
        self.app.processEvents()
        self.assertTrue(self.window.isMinimized())
        self.window.showNormal()
        self.bar.close_button.click()
        self.assertEqual(self.window.close_requests, 1)
        self.assertTrue(self.window.isVisible(), 'a rejected close must keep the app open')
        self.window.allow_close = True
        self.bar.close_button.click()
        self.assertFalse(self.window.isVisible())

    def test_drag_fallback_moves_window_and_restores_maximized_window(self):
        with patch.object(QtGui.QWindow, 'startSystemMove', return_value=False):
            start = self.bar.mapToGlobal(self.bar.rect().center())
            old = self.window.pos()
            self.mouse(self.bar, QtCore.QEvent.MouseButtonPress, start, QtCore.Qt.LeftButton)
            self.mouse(self.bar, QtCore.QEvent.MouseMove, start + QtCore.QPoint(70, 40))
            self.mouse(self.bar, QtCore.QEvent.MouseButtonRelease, start + QtCore.QPoint(70, 40),
                       QtCore.Qt.LeftButton, QtCore.Qt.NoButton)
            self.assertEqual(self.window.pos(), old + QtCore.QPoint(70, 40))
            self.window.showMaximized()
            self.app.processEvents()
            start = self.bar.mapToGlobal(self.bar.rect().center())
            self.mouse(self.bar, QtCore.QEvent.MouseButtonPress, start, QtCore.Qt.LeftButton)
            self.mouse(self.bar, QtCore.QEvent.MouseMove, start + QtCore.QPoint(60, 50))
            self.assertFalse(self.window.isMaximized())
            self.assertTrue(self.bar.rect().contains(self.bar.mapFromGlobal(start + QtCore.QPoint(60, 50))))

    def test_edges_resize_from_each_side_and_enforce_minimum_size(self):
        with patch.object(QtGui.QWindow, 'startSystemResize', return_value=False):
            for handle in self.bar.resize_handles:
                self.window.setGeometry(100, 100, 800, 500)
                self.app.processEvents()
                start = handle.mapToGlobal(handle.rect().center())
                before = self.window.geometry()
                self.mouse(handle, QtCore.QEvent.MouseButtonPress, start, QtCore.Qt.LeftButton)
                self.mouse(handle, QtCore.QEvent.MouseMove, start + QtCore.QPoint(30, 20))
                self.mouse(handle, QtCore.QEvent.MouseButtonRelease, start + QtCore.QPoint(30, 20),
                           QtCore.Qt.LeftButton, QtCore.Qt.NoButton)
                after = self.window.geometry()
                edges = handle.edges
                self.assertEqual(after.left() - before.left(), 30 if edges & QtCore.Qt.LeftEdge else 0)
                self.assertEqual(after.right() - before.right(), 30 if edges & QtCore.Qt.RightEdge else 0)
                self.assertEqual(after.top() - before.top(), 20 if edges & QtCore.Qt.TopEdge else 0)
                self.assertEqual(after.bottom() - before.bottom(), 20 if edges & QtCore.Qt.BottomEdge else 0)
            handle = next(h for h in self.bar.resize_handles if h.edges == QtCore.Qt.LeftEdge)
            before = self.window.geometry()
            start = handle.mapToGlobal(handle.rect().center())
            self.mouse(handle, QtCore.QEvent.MouseButtonPress, start, QtCore.Qt.LeftButton)
            self.mouse(handle, QtCore.QEvent.MouseMove, start + QtCore.QPoint(2000, 0))
            self.assertEqual(self.window.width(), self.window.minimumWidth())
            self.assertEqual(self.window.geometry().right(), before.right())

    def test_resize_handles_hide_while_maximized_or_fullscreen_and_do_not_cover_dialogs(self):
        self.assertTrue(all(h.isVisible() for h in self.bar.resize_handles))
        for show in (self.window.showMaximized, self.window.showFullScreen):
            show()
            self.app.processEvents()
            self.assertFalse(any(h.isVisible() for h in self.bar.resize_handles))
        self.window.showNormal()
        self.app.processEvents()
        self.assertTrue(all(h.isVisible() for h in self.bar.resize_handles))
        dialog = QtWidgets.QDialog(self.window)
        dialog.show()
        self.app.processEvents()
        self.assertTrue(all(h.window() is self.window for h in self.bar.resize_handles))
        dialog.close()

    def test_native_move_and_resize_are_delegated_to_window_manager(self):
        with patch.object(QtGui.QWindow, 'startSystemMove', return_value=True) as move:
            start = self.bar.mapToGlobal(self.bar.rect().center())
            before = self.window.geometry()
            self.mouse(self.bar, QtCore.QEvent.MouseButtonPress, start, QtCore.Qt.LeftButton)
            self.mouse(self.bar, QtCore.QEvent.MouseMove, start + QtCore.QPoint(30, 20))
            move.assert_called_once_with()
            self.assertEqual(self.window.geometry(), before)
        handle = self.bar.resize_handles[0]
        with patch.object(QtGui.QWindow, 'startSystemResize', return_value=True) as resize:
            self.mouse(handle, QtCore.QEvent.MouseButtonPress, handle.mapToGlobal(handle.rect().center()), QtCore.Qt.LeftButton)
            resize.assert_called_once_with(handle.edges)

    def test_dark_theme_keeps_window_controls_readable(self):
        from yolo_backprop.ui_theme import widget_stylesheet
        self.window.setStyleSheet(widget_stylesheet(True))
        self.app.processEvents()
        self.assertGreater(self.bar.title.palette().color(QtGui.QPalette.WindowText).lightness(), 180)
        for button in (self.bar.minimize_button, self.bar.maximize_button, self.bar.close_button):
            self.assertGreater(button.palette().color(QtGui.QPalette.ButtonText).lightness(), 180)
            self.assertTrue(button.accessibleName())
