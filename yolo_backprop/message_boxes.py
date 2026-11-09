"""One presentation for native message boxes, including static Qt calls.

Keep QMessageBox in charge of button roles, return values, default/escape keys
and details. Only its presentation is adapted; lengthy messages scroll instead
of making the modal window taller than the available screen.
"""
import math

from PyQt5 import QtCore, QtGui, QtWidgets, sip


_ZH_BUTTONS = {
    QtWidgets.QMessageBox.Ok: '确定', QtWidgets.QMessageBox.Save: '保存',
    QtWidgets.QMessageBox.SaveAll: '全部保存', QtWidgets.QMessageBox.Open: '打开',
    QtWidgets.QMessageBox.Yes: '是', QtWidgets.QMessageBox.YesToAll: '全部是',
    QtWidgets.QMessageBox.No: '否', QtWidgets.QMessageBox.NoToAll: '全部否',
    QtWidgets.QMessageBox.Abort: '中止', QtWidgets.QMessageBox.Retry: '重试',
    QtWidgets.QMessageBox.Ignore: '忽略', QtWidgets.QMessageBox.Close: '关闭',
    QtWidgets.QMessageBox.Cancel: '取消', QtWidgets.QMessageBox.Discard: '不保存',
    QtWidgets.QMessageBox.Help: '帮助', QtWidgets.QMessageBox.Apply: '应用',
    QtWidgets.QMessageBox.Reset: '重置', QtWidgets.QMessageBox.RestoreDefaults: '恢复默认',
}


def _context(box):
    """Resolve the actual workbench, even when a prompt belongs to a subdialog."""
    dark, language = None, None
    parent = box.parentWidget() or QtWidgets.QApplication.activeWindow()
    while parent is not None and parent is not box:
        if dark is None and parent.property('darkMode') is not None:
            dark = bool(parent.property('darkMode'))
        if language is None:
            language = getattr(parent, 'cfg', {}).get('software', {}).get('language')
        parent = parent.parentWidget()
    return bool(dark), language or 'zh'


def _stylesheet(dark):
    bg, text, border, button, hover = (
        ('#242426', '#f5f5f7', '#55555b', '#363639', '#454549') if dark else
        ('#fafafa', '#1d1d1f', '#d5d5da', '#ffffff', '#f0f0f3'))
    return '''
        QMessageBox { background: %s; }
        QMessageBox QWidget { font-family: "Noto Sans CJK SC"; font-size: 14px;
            color: %s; background: transparent; }
        QMessageBox QLabel { padding: 0; border: none; }
        QMessageBox QTextEdit { background: %s; color: %s; border: 1px solid %s;
            border-radius: 6px; padding: 4px; }
        QMessageBox QTextBrowser#PromptBody { border: none; padding: 0; }
        QMessageBox QPushButton { background: %s; color: %s;
            border: 1px solid %s; border-radius: 8px; padding: 6px 14px;
            min-width: 60px; min-height: 22px; margin: 0; }
        QMessageBox QPushButton:hover { background: %s; }
        QMessageBox QPushButton:default { background: #007aff; color: white; border-color: #007aff; }
        QMessageBox QPushButton:default:hover { background: #1987ff; }
        QMessageBox QPushButton[promptDestructive="true"] { color: %s; }
        QMessageBox QPushButton:focus { border: 2px solid #007aff; padding: 5px 13px; }
        QMessageBox QScrollBar:vertical { background: %s; width: 10px; margin: 0; }
        QMessageBox QScrollBar::handle:vertical { background: #98989d; min-height: 20px; border-radius: 5px; }
        QMessageBox QScrollBar::add-line:vertical, QMessageBox QScrollBar::sub-line:vertical { height: 0; }
        QMessageBox QScrollBar::add-page:vertical, QMessageBox QScrollBar::sub-page:vertical { background: transparent; }
    ''' % (bg, text, bg, text, border, button, text, border, hover,
           '#ff848a' if dark else '#c72c36', bg)


class _MessageBoxPresentation(QtCore.QObject):
    def eventFilter(self, box, event):
        if not isinstance(box, QtWidgets.QMessageBox):
            return False
        if event.type() == QtCore.QEvent.Show:
            self._show(box)
        elif (event.type() == QtCore.QEvent.LayoutRequest and box.isVisible()
              and hasattr(box, '_prompt_body')):
            self._fit(box)
            return True  # The hidden native label no longer determines size.
        return False

    def _show(self, box):
        if sip.isdeleted(box) or not box.isVisible():
            return
        self._prepare(box)
        self._fit(box)

    def _prepare(self, box):
        dark, language = _context(box)
        box._prompt_language = language
        box._prompt_layout_signature = None
        box.setStyleSheet(_stylesheet(dark))
        if language == 'zh' and box.windowTitle().lower() in ('warning', 'information', 'question', 'error'):
            box.setWindowTitle('操作失败' if box.windowTitle().lower() == 'error' else '提示')
        elif not box.windowTitle():
            box.setWindowTitle('提示' if language == 'zh' else 'Notice')
        # Reuse Qt 5's grid and preserve its labels: native updateSize() still
        # dereferences them. Qt can rebuild this grid when a reused message box
        # receives informative text, so reattach our body on every Show.
        label = box.findChild(QtWidgets.QLabel, 'qt_msgbox_label')
        if label is None:
            return
        layout = box.layout()
        row, column, rows, columns = layout.getItemPosition(layout.indexOf(label))
        label.hide()
        info = box.findChild(QtWidgets.QLabel, 'qt_msgbox_informativelabel')
        if info is not None:
            info.hide()
        box._prompt_native_labels = (label, info)
        if not hasattr(box, '_prompt_body'):
            body = QtWidgets.QTextBrowser(box)
            body.setObjectName('PromptBody')
            body.setFrameShape(QtWidgets.QFrame.NoFrame)
            body.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            body.setWordWrapMode(QtGui.QTextOption.WrapAtWordBoundaryOrAnywhere)
            body.setOpenExternalLinks(True)
            body.setFocusPolicy(QtCore.Qt.ClickFocus)
            body.document().setDocumentMargin(0)
            box._prompt_body = body
        body = box._prompt_body
        if layout.indexOf(body) < 0:
            layout.addWidget(body, row, column, rows, columns)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(16)
        if box.textFormat() == QtCore.Qt.PlainText:
            body.setPlainText(box.text())
        elif box.textFormat() == QtCore.Qt.RichText:
            body.setHtml(box.text())
        else:
            body.setText(box.text())
        if box.informativeText():
            body.append(box.informativeText())
        body.setAccessibleName(box.windowTitle())
        body.ensurePolished()
        detail_labels = {QtCore.QCoreApplication.translate('QMessageBox', label)
                         for label in ('Show Details...', 'Hide Details...')}
        for button in box.buttons():
            if (box.buttonRole(button) == QtWidgets.QMessageBox.ActionRole
                    and box.detailedText() and button.text() in detail_labels
                    and not button.property('promptDetailsConnected')):
                box._prompt_details_button = button
                button.setProperty('promptDetailsConnected', True)
                button.clicked.connect(lambda checked=False, target=box:
                    QtCore.QTimer.singleShot(0, lambda: self._fit_if_visible(target)))

    def _fit_if_visible(self, box):
        if not sip.isdeleted(box) and box.isVisible():
            self._fit(box)

    def _fit(self, box):
        if not hasattr(box, '_prompt_body') or getattr(box, '_prompt_fitting', False):
            return
        box._prompt_fitting = True
        try:
            self._layout(box)
        finally:
            box._prompt_fitting = False

    def _layout(self, box):
        body = box._prompt_body
        screen = box.screen() or QtWidgets.QApplication.primaryScreen()
        available = screen.availableGeometry()
        details = [editor for editor in box.findChildren(QtWidgets.QTextEdit)
                   if editor is not body and editor.isVisibleTo(box)]
        for button in box.buttons():
            standard = box.standardButton(button)
            text = button.text()
            if box._prompt_language == 'zh':
                if standard in _ZH_BUTTONS:
                    text = _ZH_BUTTONS[standard]
                elif button is getattr(box, '_prompt_details_button', None):
                    text = '收起详情' if details else '查看详情'
            if button.text() != text:
                button.setText(text)
            destructive = box.buttonRole(button) == QtWidgets.QMessageBox.DestructiveRole
            if button.property('promptDestructive') != destructive:
                button.setProperty('promptDestructive', destructive)
                button.style().unpolish(button)
                button.style().polish(button)
            button.ensurePolished()
            if button is getattr(box, '_prompt_details_button', None):
                # Qt's private details button reserves space for its original
                # English labels even after translation. Measure the displayed
                # label so a short Chinese action does not force a vertical row.
                button.setFixedWidth(max(90, button.fontMetrics().horizontalAdvance(button.text()) + 30))
        signature = (available.getRect(), bool(details), box.text(), box.informativeText(),
                     body.font().toString(), tuple((button.text(), button.sizeHint().width(),
                     button.sizeHint().height()) for button in box.buttons()))
        if (signature == box._prompt_layout_signature
                and box.size() == getattr(box, '_prompt_layout_size', None)
                and box.layout().totalSizeHint() == box.size()):
            return
        buttons = box.findChild(QtWidgets.QDialogButtonBox)
        width = min(480, available.width() - 128)
        buttons.setOrientation(QtCore.Qt.Horizontal)
        row_width = buttons.sizeHint().width()
        buttons.setOrientation(QtCore.Qt.Vertical if row_width > available.width() - 64 else QtCore.Qt.Horizontal)
        width = max(min(320, available.width() - 128), min(width, row_width))
        body.setFixedWidth(width)
        # Leave room for window decorations and the action row on small/high-DPI
        # screens. Both message text and optional technical details can scroll.
        budget = available.height() - 96 - buttons.sizeHint().height()
        details_height = min(120, max(32, budget // 3)) if details else 0
        for editor in details:
            editor.setFixedHeight(details_height)
            editor.setMinimumWidth(0)
            # Its native container caches the original 100px editor height.
            # Refresh that nested layout before calculating the body budget.
            detail_layout = editor.parentWidget().layout()
            if detail_layout is not None:
                detail_layout.invalidate()
                detail_layout.activate()
        body.document().setTextWidth(max(1, width - 12))
        height = math.ceil(body.document().size().height()) + 4
        body.setFixedHeight(max(32, min(height, budget - details_height - (24 if details else 0))))
        box.layout().invalidate()
        box.layout().activate()
        extra = box.layout().totalSizeHint().height() - (available.height() - 48)
        if extra > 0:
            body.setFixedHeight(max(32, body.height() - extra))
            box.layout().invalidate()
            box.layout().activate()
        box.setFixedSize(box.layout().totalSizeHint())
        box._prompt_layout_signature = signature
        box._prompt_layout_size = box.size()
        # A formerly oversized native message may already have been positioned
        # against a screen edge before Show. Keep the complete frame in bounds.
        frame = box.frameGeometry()
        x = max(available.left(), min(frame.left(), available.right() - frame.width() + 1))
        y = max(available.top(), min(frame.top(), available.bottom() - frame.height() + 1))
        box.move(box.pos() + QtCore.QPoint(x - frame.left(), y - frame.top()))


def install_message_box_theme():
    """Install once per application; static calls and plugin prompts participate."""
    app = QtWidgets.QApplication.instance()
    if app is not None and not hasattr(app, '_message_box_presentation'):
        app._message_box_presentation = _MessageBoxPresentation(app)
        app.installEventFilter(app._message_box_presentation)
