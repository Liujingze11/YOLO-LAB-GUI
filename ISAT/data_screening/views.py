"""Read-only image drag/drop and a three-column thumbnail grid."""
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from .session import IMAGE_SUFFIXES


IMAGE_MIME = 'application/x-yolo-backprop-screening-image'
PREVIEW_MIME = 'application/x-yolo-backprop-preview'


def dropped_folder(mime):
    urls = mime.urls() if mime.hasUrls() else []
    if len(urls) == 1 and urls[0].isLocalFile() and Path(urls[0].toLocalFile()).is_dir():
        return urls[0].toLocalFile()
    return None


def dropped_image(mime):
    if mime.hasFormat(IMAGE_MIME):
        try: path = bytes(mime.data(IMAGE_MIME)).decode('utf-8')
        except UnicodeError: return None
    else:
        urls = mime.urls() if mime.hasUrls() else []
        if len(urls) != 1 or not urls[0].isLocalFile(): return None
        path = urls[0].toLocalFile()
    file = Path(path)
    return str(file.resolve()) if file.is_file() and file.suffix.lower() in IMAGE_SUFFIXES else None


def accept_copy(event):
    if event.possibleActions() & QtCore.Qt.CopyAction:
        event.setDropAction(QtCore.Qt.CopyAction); event.accept()
    else:
        event.ignore()


class FolderGrid(QtWidgets.QListWidget):
    folder_dropped = QtCore.pyqtSignal(str)
    drag_anchor_requested = QtCore.pyqtSignal()
    image_drag_started = QtCore.pyqtSignal()
    image_drag_finished = QtCore.pyqtSignal(bool)
    preview_returned = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(self.IconMode)
        self.setResizeMode(self.Adjust)
        self.setMovement(self.Static)
        self.setSelectionMode(self.ExtendedSelection)
        self.setSpacing(0)
        self.setWordWrap(True)
        self.setTextElideMode(QtCore.Qt.ElideMiddle)
        self.setMinimumWidth(260)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDefaultDropAction(QtCore.Qt.CopyAction)
        self.viewport().setAcceptDrops(True)
        self._layout_columns()

    def _layout_columns(self):
        # QListView wraps a cell ending exactly at the viewport's right edge.
        width = max(1, (self.viewport().width() - 1) // 3)
        image_width = min(180, max(32, width - 20))
        image_height = image_width * 3 // 4
        self.setIconSize(QtCore.QSize(image_width, image_height))
        self.setGridSize(QtCore.QSize(width, image_height + self.fontMetrics().height() * 2 + 16))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_columns()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton: self.drag_anchor_requested.emit()
        super().mousePressEvent(event)

    def mimeData(self, items):
        mime = QtCore.QMimeData()
        if items:
            asset = items[0].data(QtCore.Qt.UserRole)
            if asset:
                path = str(asset.source)
                mime.setData(IMAGE_MIME, path.encode('utf-8'))
                mime.setUrls([QtCore.QUrl.fromLocalFile(path)])
        return mime

    def startDrag(self, supported_actions):
        current = self.currentItem()
        if current is None: return
        mime = self.mimeData([current])
        if not dropped_image(mime): return
        self.image_drag_started.emit()
        drag = QtGui.QDrag(self); drag.setMimeData(mime)
        drag.setPixmap(current.icon().pixmap(96, 72))
        drag.setHotSpot(QtCore.QPoint(48, 36))
        result = drag.exec_(QtCore.Qt.CopyAction, QtCore.Qt.CopyAction)
        self.image_drag_finished.emit(result == QtCore.Qt.CopyAction)

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        accept_copy(event) if dropped_folder(mime) or (mime.hasFormat(PREVIEW_MIME) and dropped_image(mime)) else event.ignore()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        folder = dropped_folder(event.mimeData())
        if folder:
            accept_copy(event)
            if event.isAccepted(): self.folder_dropped.emit(folder)
        elif event.mimeData().hasFormat(PREVIEW_MIME) and dropped_image(event.mimeData()):
            accept_copy(event)
            if event.isAccepted(): self.preview_returned.emit(dropped_image(event.mimeData()))
        else:
            event.ignore()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.count():
            painter = QtGui.QPainter(self.viewport())
            painter.setPen(self.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Text))
            painter.drawText(self.viewport().rect().adjusted(24, 24, -24, -24),
                             QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
                             '将图片文件夹拖到这里\n或点击“打开文件夹”')


class TrashStrip(QtWidgets.QListWidget):
    """One horizontal row of recoverable photos; it never accepts image drops."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('ScreeningTrashStrip')
        self.setViewMode(self.IconMode)
        self.setFlow(self.LeftToRight); self.setWrapping(False)
        self.setMovement(self.Static); self.setResizeMode(self.Adjust)
        self.setSelectionMode(self.ExtendedSelection)
        self.setIconSize(QtCore.QSize(72, 54)); self.setGridSize(QtCore.QSize(96, 82))
        self.setFixedHeight(104)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setAcceptDrops(False); self.setDragEnabled(False)
        self.setTextElideMode(QtCore.Qt.ElideMiddle)
        self.setToolTip('双击恢复图片；可多选后恢复。')

    def event(self, event):
        if event.type() == QtCore.QEvent.ShortcutOverride:
            if event.key() in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Right, QtCore.Qt.Key_Delete, QtCore.Qt.Key_F2) or (
                    event.key() == QtCore.Qt.Key_A and event.modifiers() == QtCore.Qt.ControlModifier):
                event.accept(); return True
        return super().event(event)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_F2):
            event.accept(); return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.count():
            painter = QtGui.QPainter(self.viewport())
            painter.setPen(self.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Text))
            painter.drawText(self.viewport().rect(), QtCore.Qt.AlignCenter, '移除的图片会显示在这里')


class ImagePreview(QtWidgets.QGraphicsView):
    image_dropped = QtCore.pyqtSignal(str, str)
    folder_dropped = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QtWidgets.QGraphicsScene(self))
        self.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        self.viewport().setAutoFillBackground(False)
        self.setDragMode(self.NoDrag)
        self.setTransformationAnchor(self.AnchorUnderMouse)
        self.setAcceptDrops(True)
        self.displayed_path = None
        self._fit = True
        self.allow_compare = False
        self._drop_hint = None
        self._drag_origin = None
        self._pan_origin = None
        self.setToolTip('左键拖动图片到左栏可移出预览；中键平移，滚轮缩放。')

    def _drop_mode(self, position):
        return 'compare' if self.allow_compare and position.x() >= self.viewport().width() * .72 else 'replace'

    def dragEnterEvent(self, event):
        if dropped_image(event.mimeData()) or dropped_folder(event.mimeData()):
            accept_copy(event)
            self._drop_hint = self._drop_mode(event.pos()) if dropped_image(event.mimeData()) else None
            self.viewport().update()
        else: event.ignore()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        self._drop_hint = None; self.viewport().update(); event.accept()

    def dropEvent(self, event):
        image, folder = dropped_image(event.mimeData()), dropped_folder(event.mimeData())
        if image or folder:
            accept_copy(event)
            if event.isAccepted():
                if image: self.image_dropped.emit(image, self._drop_mode(event.pos()))
                else: self.folder_dropped.emit(folder)
        else:
            event.ignore()
        self._drop_hint = None; self.viewport().update()

    def mime_data(self):
        mime = QtCore.QMimeData()
        if self.displayed_path:
            mime.setData(IMAGE_MIME, self.displayed_path.encode('utf-8'))
            mime.setData(PREVIEW_MIME, b'preview')
            mime.setUrls([QtCore.QUrl.fromLocalFile(self.displayed_path)])
        return mime

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.displayed_path:
            self._drag_origin = event.pos()
        if event.button() == QtCore.Qt.MiddleButton:
            self._pan_origin = event.pos(); self.setCursor(QtCore.Qt.ClosedHandCursor)
            event.accept(); return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan_origin is not None and event.buttons() & QtCore.Qt.MiddleButton:
            delta = event.pos() - self._pan_origin; self._pan_origin = event.pos(); self._fit = False
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept(); return
        if (self._drag_origin is not None and self.displayed_path and event.buttons() & QtCore.Qt.LeftButton
                and (event.pos() - self._drag_origin).manhattanLength() >= QtWidgets.QApplication.startDragDistance()):
            self._drag_origin = None
            drag = QtGui.QDrag(self); drag.setMimeData(self.mime_data())
            drag.setPixmap(self.viewport().grab().scaled(128, 96, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
            drag.exec_(QtCore.Qt.CopyAction, QtCore.Qt.CopyAction)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_origin = None
        if event.button() == QtCore.Qt.MiddleButton:
            self._pan_origin = None; self.unsetCursor(); event.accept(); return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._drop_hint:
            if not self.displayed_path:
                painter = QtGui.QPainter(self.viewport())
                painter.setPen(self.palette().color(QtGui.QPalette.Disabled, QtGui.QPalette.Text))
                painter.drawText(self.viewport().rect().adjusted(20, 20, -20, -20),
                                 QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap, '拖入图片到这里')
            return
        painter = QtGui.QPainter(self.viewport())
        rect = self.viewport().rect().adjusted(6, 6, -6, -6)
        if self.allow_compare:
            split = int(self.viewport().width() * .72)
            rect = QtCore.QRect(split, rect.top(), rect.right() - split, rect.height()) if self._drop_hint == 'compare' else QtCore.QRect(rect.left(), rect.top(), split - rect.left() - 4, rect.height())
        painter.fillRect(rect, QtGui.QColor(240, 246, 255, 220))
        painter.setPen(QtGui.QPen(QtGui.QColor('#3469a8'), 2, QtCore.Qt.DashLine)); painter.drawRect(rect)
        painter.drawText(rect.adjusted(8, 8, -8, -8), QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
                         '松开加入对比' if self._drop_hint == 'compare' else '松开替换图片')

    def show_image(self, path, image):
        self.scene().clear()
        self.scene().addPixmap(QtGui.QPixmap.fromImage(image))
        self.scene().setSceneRect(QtCore.QRectF(image.rect()))
        self.displayed_path = path
        self.fit_image()

    def clear_image(self):
        self.scene().clear()
        self.displayed_path = None

    def fit_image(self):
        self._fit = True
        if self.displayed_path: self.fitInView(self.sceneRect(), QtCore.Qt.KeepAspectRatio)

    def wheelEvent(self, event):
        if self.displayed_path:
            self._fit = False
            factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
            if .02 < self.transform().m11() * factor < 30: self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fit: self.fit_image()
