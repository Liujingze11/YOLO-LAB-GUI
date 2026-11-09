"""Shared window title, commands and native move/resize integration."""
from PyQt5 import QtCore, QtGui, QtWidgets


class _WindowButton(QtWidgets.QToolButton):
    def __init__(self, kind, text, parent):
        super().__init__(parent)
        self.kind = kind
        self.setObjectName('Window' + kind.title())
        self.setFixedSize(32, 30)
        self.setFocusPolicy(QtCore.Qt.TabFocus)
        self.setToolTip(text)
        self.setAccessibleName(text)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtGui.QPen(self.palette().color(QtGui.QPalette.ButtonText), 1.25))
        painter.translate(self.rect().center())
        if self.kind == 'minimize':
            painter.drawLine(-5, 0, 5, 0)
        elif self.kind == 'close':
            painter.drawLine(-4, -4, 4, 4)
            painter.drawLine(-4, 4, 4, -4)
        elif self.kind == 'restore':
            painter.drawPolyline(QtGui.QPolygon([QtCore.QPoint(-2, -4), QtCore.QPoint(-2, -6),
                                                QtCore.QPoint(6, -6), QtCore.QPoint(6, 2), QtCore.QPoint(4, 2)]))
            painter.drawRect(-5, -3, 8, 8)
        else:
            painter.drawRect(-5, -5, 10, 10)


class _ResizeHandle(QtWidgets.QWidget):
    """An edge hit area; Qt delegates snapping and resizing to the desktop."""
    def __init__(self, window, edges):
        super().__init__(window)
        self.edges = edges
        self._origin = None
        self.setObjectName('WindowResizeHandle')
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        horizontal = edges & (QtCore.Qt.LeftEdge | QtCore.Qt.RightEdge)
        vertical = edges & (QtCore.Qt.TopEdge | QtCore.Qt.BottomEdge)
        diagonal = edges in (QtCore.Qt.TopEdge | QtCore.Qt.LeftEdge,
                             QtCore.Qt.BottomEdge | QtCore.Qt.RightEdge)
        self.setCursor((QtCore.Qt.SizeFDiagCursor if diagonal else QtCore.Qt.SizeBDiagCursor)
                       if horizontal and vertical else
                       QtCore.Qt.SizeHorCursor if horizontal else QtCore.Qt.SizeVerCursor)

    def mousePressEvent(self, event):
        window = self.window()
        if event.button() != QtCore.Qt.LeftButton or window.isMaximized() or window.isFullScreen():
            return super().mousePressEvent(event)
        self._origin = None
        native = getattr(window.windowHandle(), 'startSystemResize', None)
        if not native or not native(self.edges):
            self._origin = (event.globalPos(), window.geometry())
        event.accept()

    def mouseMoveEvent(self, event):
        if self._origin is None or not event.buttons() & QtCore.Qt.LeftButton:
            return super().mouseMoveEvent(event)
        start, rect = self._origin
        delta = event.globalPos() - start
        window = self.window()
        minimum = window.minimumSize().expandedTo(window.minimumSizeHint())
        maximum = window.maximumSize()
        result = QtCore.QRect(rect)
        if self.edges & (QtCore.Qt.LeftEdge | QtCore.Qt.RightEdge):
            left = bool(self.edges & QtCore.Qt.LeftEdge)
            width = max(minimum.width(), min(maximum.width(), rect.width() + (-delta.x() if left else delta.x())))
            result.setWidth(width)
            if left: result.moveRight(rect.right())
        if self.edges & (QtCore.Qt.TopEdge | QtCore.Qt.BottomEdge):
            top = bool(self.edges & QtCore.Qt.TopEdge)
            height = max(minimum.height(), min(maximum.height(), rect.height() + (-delta.y() if top else delta.y())))
            result.setHeight(height)
            if top: result.moveBottom(rect.bottom())
        window.setGeometry(result)
        event.accept()

    def mouseReleaseEvent(self, event):
        self._origin = None
        super().mouseReleaseEvent(event)


class WorkbenchTitleBar(QtWidgets.QFrame):
    """A single row shared by the home, screening, annotation and model pages."""
    def __init__(self, window):
        super().__init__(window)
        self._window = window
        self._drag_start = None
        self._moving = False
        window.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)
        self.setObjectName('WorkbenchTitleBar')
        self.setFixedHeight(44)
        self.setMinimumWidth(320)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.shortcut_button = QtWidgets.QToolButton(self)
        self.shortcut_button.setText('快捷键')
        self.shortcut_button.setToolTip('设置数据筛选、数据标注和模型开发的快捷键')
        self.shortcut_button.setAccessibleName('快捷键设置')
        self.shortcut_button.setFixedSize(88, 30)
        self.shortcut_button.setFocusPolicy(QtCore.Qt.TabFocus)
        self.title = QtWidgets.QLabel(self)
        self.title.setObjectName('WindowTitle')
        self.title.setAlignment(QtCore.Qt.AlignCenter)
        self.title.setTextFormat(QtCore.Qt.PlainText)
        self.title.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.minimize_button = _WindowButton('minimize', '最小化', self)
        self.maximize_button = _WindowButton('maximize', '最大化', self)
        self.close_button = _WindowButton('close', '关闭', self)
        self.minimize_button.clicked.connect(window.showMinimized)
        self.maximize_button.clicked.connect(self.toggle_maximized)
        self.close_button.clicked.connect(window.close)
        window.windowTitleChanged.connect(self._update_title)
        self.resize_handles = [_ResizeHandle(window, edges) for edges in (
            QtCore.Qt.LeftEdge, QtCore.Qt.RightEdge, QtCore.Qt.TopEdge, QtCore.Qt.BottomEdge,
            QtCore.Qt.TopEdge | QtCore.Qt.LeftEdge, QtCore.Qt.TopEdge | QtCore.Qt.RightEdge,
            QtCore.Qt.BottomEdge | QtCore.Qt.LeftEdge, QtCore.Qt.BottomEdge | QtCore.Qt.RightEdge)]
        window.installEventFilter(self)
        self._update_title()
        self._sync_window_state()

    def _update_title(self, *_):
        text = self._window.windowTitle()
        self.title.setText(self.title.fontMetrics().elidedText(text, QtCore.Qt.ElideRight, self.title.width()))
        self.title.setToolTip(text)
        self.title.setAccessibleName(text)
        # Mouse-transparent title text lets the bar handle both drag and hover.
        self.setToolTip(text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.shortcut_button.move(12, 7)
        for index, button in enumerate((self.minimize_button, self.maximize_button, self.close_button)):
            button.move(self.width() - 116 + index * 36, 7)
        # Equal reservations keep the project name centered on the window.
        self.title.setGeometry(128, 0, max(0, self.width() - 256), self.height())
        self._update_title()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QtCore.QEvent.FontChange, QtCore.QEvent.StyleChange) and hasattr(self, 'title'):
            self._update_title()

    def eventFilter(self, watched, event):
        if watched is self._window and event.type() in (
                QtCore.QEvent.Resize, QtCore.QEvent.Show, QtCore.QEvent.WindowStateChange):
            self._sync_window_state()
        return False

    def _sync_window_state(self):
        window = self._window
        expanded = window.isMaximized() or window.isFullScreen()
        self.maximize_button.kind = 'restore' if expanded else 'maximize'
        self.maximize_button.setToolTip('还原' if expanded else '最大化')
        self.maximize_button.setAccessibleName(self.maximize_button.toolTip())
        self.maximize_button.update()
        width, height, grip = window.width(), window.height(), 6
        rects = ((0, grip, grip, height - 2 * grip), (width - grip, grip, grip, height - 2 * grip),
                 (grip, 0, width - 2 * grip, grip), (grip, height - grip, width - 2 * grip, grip),
                 (0, 0, grip, grip), (width - grip, 0, grip, grip),
                 (0, height - grip, grip, grip), (width - grip, height - grip, grip, grip))
        for handle, rect in zip(self.resize_handles, rects):
            handle.setGeometry(*rect)
            handle.setVisible(window.isVisible() and not expanded and not window.isMinimized())
            handle.raise_()

    def toggle_maximized(self):
        if self._window.isMaximized() or self._window.isFullScreen():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_start = None
            self.toggle_maximized()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and not self._window.isFullScreen():
            self._drag_start = event.globalPos()
            self._drag_offset = event.globalPos() - self._window.pos()
            self._moving = False
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start is None or not event.buttons() & QtCore.Qt.LeftButton:
            return super().mouseMoveEvent(event)
        window = self._window
        if not self._moving:
            if (event.globalPos() - self._drag_start).manhattanLength() < QtWidgets.QApplication.startDragDistance():
                return
            if window.isMaximized():
                fraction = self._drag_offset.x() / max(1, window.width())
                window.showNormal()
                self._drag_offset.setX(round(window.width() * fraction))
                window.move(event.globalPos() - self._drag_offset)
            native = getattr(window.windowHandle(), 'startSystemMove', None)
            if native and native():
                self._drag_start = None
                return
            self._moving = True
        window.move(event.globalPos() - self._drag_offset)
        event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        self._moving = False
        super().mouseReleaseEvent(event)
