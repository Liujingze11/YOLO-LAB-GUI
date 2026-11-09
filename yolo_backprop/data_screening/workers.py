"""Background image reading and project copying; pixmaps stay on the GUI thread."""
from io import BytesIO

from PIL import Image
from PyQt5 import QtCore, QtGui

from .session import ScreeningSession


class Cancelled(RuntimeError):
    pass


def read_image(path, side):
    reader = QtGui.QImageReader(str(path))
    reader.setAutoTransform(False)  # Match the original ISAT canvas coordinates.
    size = reader.size()
    if size.isValid() and max(size.width(), size.height()) > side:
        reader.setScaledSize(size.scaled(side, side, QtCore.Qt.KeepAspectRatio))
    image = reader.read()
    if image.isNull():
        with Image.open(path) as source:
            source.thumbnail((side, side))
            buffer = BytesIO()
            source.convert('RGB').save(buffer, format='PNG')
            image = QtGui.QImage.fromData(buffer.getvalue())
    if image.isNull():
        raise ValueError('无法预览图片：' + str(path))
    return image


class BackgroundWorker(QtCore.QThread):
    failed = QtCore.pyqtSignal(str)
    progress = QtCore.pyqtSignal(int, int, str)

    def stop(self):
        self.requestInterruption()

    def check_cancelled(self):
        if self.isInterruptionRequested(): raise Cancelled()


class ScanWorker(BackgroundWorker):
    loaded = QtCore.pyqtSignal(object)
    thumbnail = QtCore.pyqtSignal(str, QtGui.QImage)

    def __init__(self, root, parent=None, workspace=None, project=False):
        super().__init__(parent)
        self.root = root
        self.workspace, self.project = workspace, project

    def run(self):
        try:
            if self.workspace:
                session = (self.workspace.open_project(self.root) if self.project else
                           self.workspace.import_folder(self.root, self.check_cancelled, self.progress.emit))
            else:
                session = ScreeningSession.scan(self.root, self.check_cancelled, self.progress.emit)
            self.check_cancelled()
            self.loaded.emit(session)
            items = session.items + session.trash
            for index, item in enumerate(items):
                self.check_cancelled()
                try:
                    self.thumbnail.emit(str(item.source), read_image(item.source, 128))
                except (OSError, ValueError):
                    pass  # Keep valid sources even if their thumbnail reader fails.
                self.progress.emit(index + 1, len(items), item.name)
        except Cancelled:
            pass
        except Exception as exc:
            self.failed.emit(str(exc))


class PreviewWorker(BackgroundWorker):
    ready = QtCore.pyqtSignal(str, QtGui.QImage)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path

    def run(self):
        try:
            self.check_cancelled()
            image = read_image(self.path, 2048)
            self.check_cancelled()
            self.ready.emit(self.path, image)
        except Cancelled:
            pass
        except Exception as exc:
            self.failed.emit(str(exc))


class ExportWorker(BackgroundWorker):
    ready = QtCore.pyqtSignal(dict)

    def __init__(self, session, destination, categories, parent=None):
        super().__init__(parent)
        self.session, self.destination, self.categories = session, destination, categories

    def run(self):
        try:
            result = self.session.export_project(self.destination, self.check_cancelled,
                                                 self.progress.emit, self.categories)
            self.ready.emit(result)
        except Cancelled:
            pass
        except Exception as exc:
            self.failed.emit(str(exc))


class SaveWorker(BackgroundWorker):
    ready = QtCore.pyqtSignal(dict)

    def __init__(self, session, categories, parent=None, purge=False):
        super().__init__(parent)
        self.session, self.categories, self.purge = session, categories, purge
        self.result = None

    def run(self):
        try:
            from .workspace import save_project
            self.result = (save_project(self.session, self.check_cancelled, self.progress.emit, purge=True)
                           if self.purge else self.session.save_project(self.check_cancelled, self.progress.emit, self.categories))
            self.ready.emit(self.result)
        except Cancelled: pass
        except Exception as exc: self.failed.emit(str(exc))
