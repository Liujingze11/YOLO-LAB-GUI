import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import threading
import unittest
from PyQt5 import QtCore, QtWidgets


class OperationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_operation_runs_off_gui_thread_while_gui_events_continue(self):
        from yolo_backprop.workspaces.operations import run_operation
        main_thread = threading.get_ident(); event = threading.Event()
        QtCore.QTimer.singleShot(10, event.set)
        def operation(check, progress):
            self.assertNotEqual(threading.get_ident(), main_thread)
            self.assertTrue(event.wait(2))
            progress(1, 1, '完成')
            return {'images': 2}
        self.assertEqual(run_operation(None, '识别项目', operation), {'images': 2})

    def test_cancel_waits_for_worker_cleanup_and_returns_no_result(self):
        from yolo_backprop.workspaces.operations import run_operation
        cleaned = []
        def cancel():
            dialog = self.app.activeModalWidget()
            if dialog: dialog.cancel_button.click()
        QtCore.QTimer.singleShot(10, cancel)
        def operation(check, progress):
            try:
                for _ in range(1000):
                    check(); QtCore.QThread.msleep(1)
                raise AssertionError('cancel was not delivered')
            finally: cleaned.append(True)
        self.assertIsNone(run_operation(None, '整理项目', operation))
        self.assertEqual(cleaned, [True])

    def test_worker_error_reaches_caller_without_a_partial_result(self):
        from yolo_backprop.workspaces.operations import run_operation
        def operation(check, progress): raise ValueError('invalid labels')
        with self.assertRaisesRegex(ValueError, 'invalid labels'):
            run_operation(None, '识别项目', operation)
