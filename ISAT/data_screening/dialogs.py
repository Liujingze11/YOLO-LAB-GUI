"""Native dialog for reversible screening trash."""
from PyQt5 import QtCore, QtWidgets


class TrashDialog(QtWidgets.QDialog):
    def __init__(self, session, restore, parent=None):
        super().__init__(parent)
        self.session, self.restore = session, restore
        self.setWindowTitle('回收站 · 仅项目副本'); self.resize(540, 400)
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel('选中后可恢复。保存成功后会询问是否永久清理这些副本。')
        label.setWordWrap(True); layout.addWidget(label)
        self.list = QtWidgets.QListWidget(); self.list.setSelectionMode(self.list.ExtendedSelection)
        for asset in session.trash:
            row = QtWidgets.QListWidgetItem(asset.name)
            row.setData(QtCore.Qt.UserRole, asset); self.list.addItem(row)
        layout.addWidget(self.list, 1)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        restore_button = buttons.addButton('恢复选中图片', buttons.ActionRole)
        restore_button.clicked.connect(self.restore_selected)
        buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def restore_selected(self):
        items = [row.data(QtCore.Qt.UserRole) for row in self.list.selectedItems()]
        if items: self.restore(items); self.accept()
