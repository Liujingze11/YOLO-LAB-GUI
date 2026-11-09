"""Shared chrome around the native work pages; page objects remain independent."""
from PyQt5 import QtCore, QtWidgets


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
        row = QtWidgets.QHBoxLayout(self.header)
        row.setContentsMargins(20, 0, 20, 0)
        row.setSpacing(24)
        row.addWidget(self.title)
        row.addStretch()
        self.body = QtWidgets.QVBoxLayout(self)
        self.body.setContentsMargins(16, 12, 16, 12)
        self.body.setSpacing(12)
        self.body.addWidget(self.header)
        self.body.addWidget(stack, 1)

    def set_page(self, title, home=False):
        self.header.setVisible(not home)
        self.title.setText(title)
        margins = (0, 0, 0, 0) if home else (16, 12, 16, 12)
        self.body.setContentsMargins(*margins)
        self.body.setSpacing(0 if home else 12)
