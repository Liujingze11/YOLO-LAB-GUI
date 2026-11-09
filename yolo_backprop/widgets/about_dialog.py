# -*- coding: utf-8 -*-
# @Author  : LG

from PyQt5 import QtCore, QtWidgets

from yolo_backprop.ui.about_dialog import Ui_Dialog


class AboutDialog(QtWidgets.QDialog, Ui_Dialog):
    def __init__(self, parent):
        super(AboutDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.setMaximumSize(640, 320)
        self.resize(600, 250)
        self.pushButton_close.clicked.connect(self.close)

    def retranslateUi(self, dialog):
        super().retranslateUi(dialog)
        from yolo_backprop import APP_NAME, PROJECT_URL, __version__

        self.setWindowTitle('关于 ' + APP_NAME)
        self.label_3.setText('<span style="font-size:14pt;">' + APP_NAME + '</span>')
        self.label_5.setText(
            '<div style="font-size:10pt;">'
            '<p>项目源码：<a href="' + PROJECT_URL + '">YOLO-LAB-GUI</a></p>'
            '<p>基于 <a href="https://github.com/yatengLG/ISAT_with_segment_anything">ISAT</a>；'
            '原版主要贡献者 <a href="https://github.com/Alias-z">Alias-z</a></p>'
            '<p>原版 Copyright (C) 2022 <a href="https://github.com/yatengLG">yatengLG</a></p></div>')

        version_text = "V{}".format(__version__)
        self.label_version.setText(version_text)
