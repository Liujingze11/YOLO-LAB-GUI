"""Real Qt dialogs: layout bounds, appearance and decision semantics."""
import unittest
from types import SimpleNamespace

from PyQt5 import QtCore, QtGui, QtTest, QtWidgets

from yolo_backprop.ui_theme import apply_window_theme, install_window_theme


class MessageBoxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.window = QtWidgets.QMainWindow()
        self.window.cfg = {'software': {'language': 'zh'}}
        self.window.model_development = SimpleNamespace(
            navigation=QtWidgets.QToolBar(self.window),
            **{name + '_action': QtWidgets.QAction(self.window)
               for name in ('home', 'screening', 'annotation', 'development')})
        install_window_theme(self.window)
        self.addCleanup(self.window.deleteLater)

    def box(self, parent=None, text='是否保存当前筛选修改？'):
        box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question, '未保存的筛选', text,
            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
            parent or self.window)
        box.setDefaultButton(QtWidgets.QMessageBox.Save)
        self.addCleanup(box.deleteLater)
        self.addCleanup(box.close)
        return box

    def show(self, box):
        box.show()
        QtTest.QTest.qWait(10)

    def assert_buttons_fit(self, box):
        for button in box.buttons():
            rect = QtCore.QRect(button.mapTo(box, QtCore.QPoint()), button.size())
            self.assertTrue(box.rect().contains(rect), (button.text(), rect, box.rect()))
            self.assertGreaterEqual(button.width(), button.fontMetrics().horizontalAdvance(button.text()) + 28)

    def test_long_message_stays_on_screen_and_can_be_read_by_scrolling(self):
        text = '无法读取图片文件，请检查目录和权限。\n' * 70
        box = self.box(text=text)
        self.show(box)
        available = box.screen().availableGeometry()
        self.assertLessEqual(box.frameGeometry().height(), available.height())
        self.assertLessEqual(box.frameGeometry().width(), available.width())
        body = box.findChild(QtWidgets.QTextBrowser, 'PromptBody')
        self.assertIsNotNone(body)
        self.assertEqual(body.toPlainText(), text)
        self.assertGreater(body.verticalScrollBar().maximum(), 0)
        self.assert_buttons_fit(box)

    def test_parent_page_styles_do_not_change_prompt_buttons(self):
        measurements = []
        for name in ('MainWindow', 'DataScreening', 'ModelDevelopment'):
            page = QtWidgets.QWidget(self.window)
            page.setObjectName(name)
            page.setStyleSheet('QWidget { font-size: 24px; } QPushButton { padding: 18px; }'
                              if name == 'ModelDevelopment' else '')
            box = self.box(page)
            self.show(box)
            save = box.button(QtWidgets.QMessageBox.Save)
            measurements.append((save.font().pixelSize(), save.size()))
            self.assertEqual(save.text(), '保存')
            self.assertEqual(box.button(QtWidgets.QMessageBox.Discard).text(), '不保存')
            self.assertEqual(box.button(QtWidgets.QMessageBox.Cancel).text(), '取消')
            self.assert_buttons_fit(box)
            box.close()
        self.assertEqual(measurements[0], measurements[1])
        self.assertEqual(measurements[1], measurements[2])

    def test_escape_and_default_keep_original_decisions(self):
        box = self.box()
        self.show(box)
        QtTest.QTest.keyClick(box, QtCore.Qt.Key_Escape)
        self.assertEqual(box.result(), QtWidgets.QMessageBox.Cancel)
        box = self.box()
        self.show(box)
        QtTest.QTest.keyClick(box, QtCore.Qt.Key_Return)
        self.assertEqual(box.result(), QtWidgets.QMessageBox.Save)

    def test_custom_destructive_buttons_and_details_keep_working(self):
        box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, '清理回收站',
                                  '是否永久删除图片副本？原始图片不会删除。', parent=self.window)
        self.addCleanup(box.deleteLater)
        self.addCleanup(box.close)
        box.setDetailedText('\n'.join('image_%s.jpg' % i for i in range(200)))
        purge = box.addButton('永久删除副本', box.DestructiveRole)
        keep = box.addButton('保留在回收站', box.RejectRole)
        box.setDefaultButton(keep)
        box.setEscapeButton(keep)
        self.show(box)
        self.assertEqual(purge.text(), '永久删除副本')
        self.assertEqual(box.buttonRole(purge), box.DestructiveRole)
        details = next(button for button in box.buttons() if button not in (keep, purge))
        details.click()
        QtTest.QTest.qWait(10)
        self.assertLessEqual(box.frameGeometry().height(), box.screen().availableGeometry().height())
        self.assertLessEqual(box.frameGeometry().width(), box.screen().availableGeometry().width())
        self.assertEqual(details.text(), '收起详情')
        body = box.findChild(QtWidgets.QTextBrowser, 'PromptBody')
        self.assertEqual(body.verticalScrollBar().maximum(), 0, 'short confirmation remains fully visible')
        self.assert_buttons_fit(box)
        QtTest.QTest.keyClick(box, QtCore.Qt.Key_Escape)
        self.assertIs(box.clickedButton(), keep)

    def test_unbroken_path_wraps_without_losing_text(self):
        text = '/home/' + '很长的目录名' * 100 + '/image.jpg'
        box = self.box(text=text)
        box.setTextFormat(QtCore.Qt.PlainText)
        self.show(box)
        body = box.findChild(QtWidgets.QTextBrowser, 'PromptBody')
        self.assertEqual(body.toPlainText(), text)
        self.assertEqual(body.horizontalScrollBar().maximum(), 0)
        self.assertTrue(box.rect().contains(QtCore.QRect(body.mapTo(box, QtCore.QPoint()), body.size())))
        self.assert_buttons_fit(box)

    def test_all_static_prompt_types_keep_their_results(self):
        for name in ('information', 'warning', 'critical', 'question'):
            captured = []
            def respond():
                box = self.app.activeModalWidget()
                body = box.findChild(QtWidgets.QTextBrowser, 'PromptBody')
                captured.append(body.toPlainText() if body else None)
                box.button(QtWidgets.QMessageBox.Cancel).click()
            QtCore.QTimer.singleShot(20, respond)
            result = getattr(QtWidgets.QMessageBox, name)(self.window, '提示', '测试内容',
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Cancel)
            self.assertEqual(captured, ['测试内容'])
            self.assertEqual(result, QtWidgets.QMessageBox.Cancel)

    def test_dark_theme_has_readable_body_and_buttons(self):
        apply_window_theme(self.window, True)
        box = self.box()
        self.show(box)
        body = box.findChild(QtWidgets.QTextBrowser, 'PromptBody')
        self.assertIsNotNone(body)
        self.assertGreater(body.palette().color(QtGui.QPalette.Text).lightness(), 180)
        self.assertLess(body.palette().color(QtGui.QPalette.Base).lightness(), 80)
        self.assert_buttons_fit(box)

    def test_reused_prompt_refreshes_rich_text_and_information(self):
        box = self.box(text='初始内容')
        self.show(box)
        box.close()
        box.setTextFormat(QtCore.Qt.RichText)
        box.setText('<b>检查失败</b>：<a href="https://example.com/help">查看帮助</a>')
        box.setInformativeText('请检查文件路径。')
        self.show(box)
        body = box.findChild(QtWidgets.QTextBrowser, 'PromptBody')
        self.assertTrue(body.isVisibleTo(box))
        self.assertGreaterEqual(box.layout().indexOf(body), 0)
        self.assertIn('检查失败：查看帮助', body.toPlainText())
        self.assertIn('请检查文件路径。', body.toPlainText())
        self.assertIn('https://example.com/help', body.toHtml())
        for label in box.findChildren(QtWidgets.QLabel):
            if label.objectName() in ('qt_msgbox_label', 'qt_msgbox_informativelabel'):
                self.assertFalse(label.isVisibleTo(box))

    def test_english_buttons_and_custom_actions_keep_their_labels(self):
        self.window.cfg['software']['language'] = 'en'
        box = self.box(text='Keep this change?')
        custom = box.addButton('Open log', box.ActionRole)
        box.setDetailedText('Technical details')
        self.show(box)
        self.assertEqual(box.button(QtWidgets.QMessageBox.Save).text(), 'Save')
        self.assertEqual(custom.text(), 'Open log')
        self.assert_buttons_fit(box)


if __name__ == '__main__':
    unittest.main()
