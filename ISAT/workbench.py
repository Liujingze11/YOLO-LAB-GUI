"""Shared chrome around the native work pages; page objects remain independent."""
from PyQt5 import QtCore, QtGui, QtWidgets


class ElidedLabel(QtWidgets.QLabel):
    """Keep the complete text accessible while allowing a narrow window."""
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self.setTextFormat(QtCore.Qt.PlainText)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        self.setMinimumWidth(0)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        text = self.fontMetrics().elidedText(self.text(), QtCore.Qt.ElideMiddle,
                                           self.contentsRect().width())
        self.style().drawItemText(painter, self.contentsRect(), self.alignment(),
                                 self.palette(), self.isEnabled(), text,
                                 QtGui.QPalette.WindowText)


class WorkbenchFrame(QtWidgets.QWidget):
    def __init__(self, stack, parent=None):
        super().__init__(parent)
        self.setObjectName('WorkbenchFrame')
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.header = QtWidgets.QFrame(self)
        self.header.setObjectName('WorkbenchHeader')
        self.header.setFixedHeight(64)
        self.title = QtWidgets.QLabel(self.header)
        self.title.setObjectName('WorkbenchTitle')
        self.project = ElidedLabel(parent=self.header)
        self.project.setObjectName('WorkbenchProject')
        self.project.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        row = QtWidgets.QHBoxLayout(self.header)
        row.setContentsMargins(20, 0, 20, 0)
        row.setSpacing(24)
        row.addWidget(self.title)
        row.addWidget(self.project, 1)
        self.body = QtWidgets.QVBoxLayout(self)
        self.body.setContentsMargins(16, 12, 16, 12)
        self.body.setSpacing(12)
        self.body.addWidget(self.header)
        self.body.addWidget(stack, 1)

    def set_page(self, title, project='', path='', home=False):
        self.header.setVisible(not home)
        self.title.setText(title)
        self.project.setText(project)
        self.project.setToolTip(path or project)
        margins = (0, 0, 0, 0) if home else (16, 12, 16, 12)
        self.body.setContentsMargins(*margins)
        self.body.setSpacing(0 if home else 12)
