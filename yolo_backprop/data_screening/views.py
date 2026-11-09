"""Thumbnail selection, reversible item transfers and read-only preview drops."""
import json
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from .session import IMAGE_SUFFIXES


IMAGE_MIME = 'application/x-yolo-backprop-screening-image'
PREVIEW_MIME = 'application/x-yolo-backprop-preview'
ITEMS_MIME = 'application/x-yolo-backprop-screening-items'


def dropped_items(mime):
    if not mime.hasFormat(ITEMS_MIME): return None
    try:
        data = json.loads(bytes(mime.data(ITEMS_MIME)).decode('utf-8'))
    except (UnicodeError, ValueError):
        return None
    if (not isinstance(data, dict) or not isinstance(data.get('session'), str)
            or data.get('source') not in ('images', 'trash')
            or not isinstance(data.get('ids'), list) or not data['ids']
            or not all(isinstance(value, str) and value for value in data['ids'])):
        return None
    return data


def highlight_drop(widget, active):
    if widget.property('dropActive') == active: return
    widget.setProperty('dropActive', active)
    widget.style().unpolish(widget); widget.style().polish(widget); widget.update()


def accept_transfer(event):
    # Internal transfers change screening records, never filesystem paths.
    if event.possibleActions() & QtCore.Qt.MoveAction:
        event.setDropAction(QtCore.Qt.MoveAction); event.accept()
    else:
        accept_copy(event)


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


class ThumbnailList(QtWidgets.QListWidget):
    items_dropped = QtCore.pyqtSignal(object)
    drag_anchor_requested = QtCore.pyqtSignal()
    image_drag_started = QtCore.pyqtSignal()
    image_drag_finished = QtCore.pyqtSignal(bool)

    def __init__(self, source_group, parent=None):
        super().__init__(parent)
        self.source_group = source_group
        self.session_token = ''
        self.transfer_items = lambda mime: []
        self.pointer_selecting = False
        self.drag_completed = False
        self.setSelectionMode(self.ExtendedSelection)
        self.setSelectionRectVisible(True)

    def enable_transfers(self):
        # setMovement(Static) resets these flags; apply after each list's layout.
        self.setAcceptDrops(True); self.viewport().setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDefaultDropAction(QtCore.Qt.CopyAction)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.pointer_selecting = True
            self.drag_completed = False
            self.drag_anchor_requested.emit()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.pointer_selecting = False
        super().mouseReleaseEvent(event)

    def mimeData(self, items):
        mime = QtCore.QMimeData()
        assets = [row.data(QtCore.Qt.UserRole) for row in sorted(items, key=self.row)]
        if assets:
            paths = [str(asset.source) for asset in assets]
            if len(paths) == 1: mime.setData(IMAGE_MIME, paths[0].encode('utf-8'))
            mime.setUrls([QtCore.QUrl.fromLocalFile(path) for path in paths])
            mime.setData(ITEMS_MIME, json.dumps({'session': self.session_token,
                         'source': self.source_group,
                         'ids': [asset.record_id for asset in assets]}).encode('utf-8'))
        return mime

    def startDrag(self, supported_actions):
        current = self.currentItem()
        if current is None or not self.isEnabled(): return
        items = self.selectedItems() if current.isSelected() else [current]
        mime = self.mimeData(items)
        self.drag_completed = True
        self.image_drag_started.emit()
        drag = QtGui.QDrag(self); drag.setMimeData(mime)
        pixmap = current.icon().pixmap(96, 72)
        if len(items) > 1:
            painter = QtGui.QPainter(pixmap)
            badge = QtCore.QRect(0, 0, 36, 22)
            painter.fillRect(badge, QtGui.QColor('#007aff'))
            painter.setPen(QtCore.Qt.white); painter.drawText(badge, QtCore.Qt.AlignCenter, str(len(items)))
            painter.end()
        drag.setPixmap(pixmap); drag.setHotSpot(QtCore.QPoint(48, 36))
        # Transfer targets update session membership themselves. Only advertise
        # copying to external applications so project files cannot be moved out.
        result = drag.exec_(QtCore.Qt.CopyAction, QtCore.Qt.CopyAction)
        self.pointer_selecting = False
        self.image_drag_finished.emit(result != QtCore.Qt.IgnoreAction)
        drag.deleteLater()

    def dragEnterEvent(self, event):
        if self.isEnabled() and self.transfer_items(event.mimeData()): accept_transfer(event)
        else: event.ignore()
        highlight_drop(self, event.isAccepted())

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        highlight_drop(self, False); event.accept()

    def dropEvent(self, event):
        highlight_drop(self, False)
        items = self.transfer_items(event.mimeData()) if self.isEnabled() else []
        if items:
            accept_transfer(event)
            if event.isAccepted(): self.items_dropped.emit(items)
        else: event.ignore()


class FolderGrid(ThumbnailList):
    folder_dropped = QtCore.pyqtSignal(str)
    preview_returned = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__('images', parent)
        self.setObjectName('ScreeningImageGrid')
        self.setViewMode(self.IconMode)
        self.setResizeMode(self.Adjust)
        self.setMovement(self.Static)
        self.setSpacing(0)
        self.setWordWrap(True)
        self.setTextElideMode(QtCore.Qt.ElideMiddle)
        self.setMinimumWidth(260)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setToolTip('从空白处拖动框选；Ctrl+单击多选，Shift+单击连续选择；拖到回收站移除。')
        self.empty_message = '将图片文件夹拖到这里\n或点击“打开图片文件夹”'
        self._layout_columns()
        self.enable_transfers()

    def _layout_columns(self):
        # IconMode reserves room for an AsNeeded scrollbar while laying out
        # cells, even while the bar is hidden. Use that same available width.
        available = self.maximumViewportSize().width() - self.style().pixelMetric(QtWidgets.QStyle.PM_ScrollBarExtent)
        width = max(1, (available - 1) // 3)
        image_width = min(180, max(32, width - 20))
        image_height = image_width * 3 // 4
        self.setIconSize(QtCore.QSize(image_width, image_height))
        self.setGridSize(QtCore.QSize(width, image_height + self.fontMetrics().height() * 2 + 16))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_columns()

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasFormat(ITEMS_MIME) and not mime.hasFormat(PREVIEW_MIME):
            super().dragEnterEvent(event); return
        accept_copy(event) if dropped_folder(mime) or (mime.hasFormat(PREVIEW_MIME) and dropped_image(mime)) else event.ignore()
        highlight_drop(self, event.isAccepted())

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat(ITEMS_MIME) and not event.mimeData().hasFormat(PREVIEW_MIME):
            super().dropEvent(event); return
        highlight_drop(self, False)
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
                             self.empty_message)


class FolderDropArea(QtWidgets.QFrame):
    """A folder-only drop target for the initial screening page."""
    folder_dropped = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)

    def _highlight(self, active):
        if self.property('dropActive') == active: return
        self.setProperty('dropActive', active)
        self.style().unpolish(self); self.style().polish(self); self.update()

    def dragEnterEvent(self, event):
        if self.isEnabled() and dropped_folder(event.mimeData()):
            accept_copy(event)
        else:
            event.ignore()
        self._highlight(event.isAccepted())

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        self._highlight(False)
        event.accept()

    def dropEvent(self, event):
        self._highlight(False)
        folder = dropped_folder(event.mimeData())
        if self.isEnabled() and folder:
            accept_copy(event)
            if event.isAccepted(): self.folder_dropped.emit(folder)
        else:
            event.ignore()


class ItemDropArea(QtWidgets.QWidget):
    """A transfer target that remains available when its thumbnail list is folded."""
    items_dropped = QtCore.pyqtSignal(object)
    drag_entered = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.transfer_items = lambda mime: []

    def dragEnterEvent(self, event):
        if self.isEnabled() and self.transfer_items(event.mimeData()):
            accept_transfer(event)
            if event.isAccepted(): self.drag_entered.emit()
        else: event.ignore()
        highlight_drop(self, event.isAccepted())

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        highlight_drop(self, False); event.accept()

    def dropEvent(self, event):
        highlight_drop(self, False)
        items = self.transfer_items(event.mimeData()) if self.isEnabled() else []
        if items:
            accept_transfer(event)
            if event.isAccepted(): self.items_dropped.emit(items)
        else: event.ignore()


class TrashStrip(ThumbnailList):
    """One horizontal row of recoverable photos with reversible transfers."""
    def __init__(self, parent=None):
        super().__init__('trash', parent)
        self.setObjectName('ScreeningTrashStrip')
        self.setViewMode(self.IconMode)
        self.setFlow(self.LeftToRight); self.setWrapping(False)
        self.setMovement(self.Static); self.setResizeMode(self.Adjust)
        self.setIconSize(QtCore.QSize(72, 54)); self.setGridSize(QtCore.QSize(96, 82))
        self.setFixedHeight(104)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setTextElideMode(QtCore.Qt.ElideMiddle)
        self.setToolTip('拖回图片区或双击恢复；从空白处框选，Ctrl+单击多选，Shift+单击连续选择。')
        self.enable_transfers()

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
    activated = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QtWidgets.QGraphicsScene(self))
        self.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        self.viewport().setAutoFillBackground(False)
        self.setDragMode(self.NoDrag)
        self.setTransformationAnchor(self.AnchorUnderMouse)
        self.setResizeAnchor(self.AnchorViewCenter)
        self.setAcceptDrops(True)
        self.setObjectName('ScreeningPreview')
        self.displayed_path = None
        self._fit = True
        self.allow_compare = False
        self._drop_hint = None
        self._drag_origin = None
        self._pan_origin = None
        self.resolve_drop = lambda mime, mode: mode
        self.decorate_mime = lambda mime, path: None
        self.empty_message = '拖入图片到这里'
        self.setToolTip('拖到另一侧互换，拖回列表移出预览，拖入回收站移除；中键平移，滚轮缩放。')

    def _drop_mode(self, position):
        if self.allow_compare:
            if position.x() <= self.viewport().width() * .28: return 'compare_left'
            if position.x() >= self.viewport().width() * .72: return 'compare'
        return 'replace'

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        mode = self.resolve_drop(mime, self._drop_mode(event.pos())) if dropped_image(mime) else None
        if mode is not None or dropped_folder(mime):
            accept_copy(event)
        else: event.ignore()
        self._drop_hint = mode if event.isAccepted() and mode != 'keep' else None
        self.viewport().update()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        self._drop_hint = None; self.viewport().update(); event.accept()

    def dropEvent(self, event):
        image, folder = dropped_image(event.mimeData()), dropped_folder(event.mimeData())
        mode = self.resolve_drop(event.mimeData(), self._drop_mode(event.pos())) if image else None
        if mode is not None or folder:
            accept_copy(event)
            if event.isAccepted():
                if image: self.image_dropped.emit(image, mode)
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
            self.decorate_mime(mime, self.displayed_path)
        return mime

    def mousePressEvent(self, event):
        self.activated.emit()
        if event.button() == QtCore.Qt.LeftButton and self.displayed_path:
            self._drag_origin = event.pos()
        if event.button() == QtCore.Qt.MiddleButton:
            self._pan_origin = event.pos(); self.setCursor(QtCore.Qt.ClosedHandCursor)
            event.accept(); return
        super().mousePressEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.activated.emit()

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
            pixmap = self.viewport().grab().scaled(128, 96, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            drag.setPixmap(pixmap); drag.setHotSpot(pixmap.rect().center())
            drag.exec_(QtCore.Qt.CopyAction, QtCore.Qt.CopyAction)
            drag.deleteLater()
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
                                 QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap, self.empty_message)
            return
        painter = QtGui.QPainter(self.viewport())
        rect = self.viewport().rect().adjusted(6, 6, -6, -6)
        if self.allow_compare:
            left, right = int(self.viewport().width() * .28), int(self.viewport().width() * .72)
            if self._drop_hint.endswith('compare_left'):
                rect.setRight(left - 4)
            elif self._drop_hint.endswith('compare'):
                rect.setLeft(right)
            else:
                rect.setLeft(left); rect.setRight(right - 4)
        painter.fillRect(rect, QtGui.QColor(0, 122, 255, 28))
        painter.setPen(QtGui.QPen(QtGui.QColor('#007aff'), 2, QtCore.Qt.DashLine)); painter.drawRect(rect)
        text = {'compare_left': '松开在左侧对比', 'compare': '松开在右侧对比',
                'swap': '松开互换左右图片', 'restore': '松开恢复并预览',
                'restore_compare_left': '松开恢复到左侧对比',
                'restore_compare': '松开恢复到右侧对比'}.get(self._drop_hint, '松开替换图片')
        chip = QtCore.QRect(0, 0, min(220, rect.width() - 16), 48)
        chip.moveCenter(rect.center())
        painter.setPen(QtCore.Qt.NoPen); painter.setBrush(self.palette().color(QtGui.QPalette.Window))
        painter.drawRoundedRect(chip, 8, 8)
        painter.setPen(self.palette().color(QtGui.QPalette.WindowText))
        painter.drawText(chip.adjusted(6, 4, -6, -4), QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap, text)

    def view_state(self):
        if not self.displayed_path: return None
        return (self.displayed_path, self.scene().items()[0].pixmap(), QtGui.QTransform(self.transform()),
                self._fit, self.mapToScene(self.viewport().rect().center()))

    def restore_view_state(self, state):
        if state is None:
            self.clear_image(); return
        path, pixmap, transform, fit, center = state
        self.scene().clear(); self.scene().addPixmap(pixmap)
        self.scene().setSceneRect(QtCore.QRectF(pixmap.rect()))
        self.displayed_path = path
        self._fit = fit
        if fit: self.fit_image()
        else:
            self.setTransform(transform); self.centerOn(center)

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
