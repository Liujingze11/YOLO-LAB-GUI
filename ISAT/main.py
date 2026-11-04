# -*- coding: utf-8 -*-
# @Author  : LG
# import os

import os
import sys
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from ISAT.widgets.mainwindow import MainWindow

# ubuntu18.04装其他应用时，环境崩了。。。qtapp初始化后，torch调用cuda会卡死，但先调用下cuda就不会卡死。
import torch

torch.cuda.is_available()
# (知道怎么处理该问题，请反馈下 T.T)


def main():
    # Non-headless OpenCV wheels replace this with their incompatible Qt plugins.
    if sys.platform.startswith("linux") and "cv2" in Path(
        os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH", "")
    ).parts:
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = QtCore.QLibraryInfo.location(
            QtCore.QLibraryInfo.PluginsPath
        )
    app = QtWidgets.QApplication(["ISAT"])
    app.setApplicationName("ISAT")
    app.setApplicationDisplayName("YOLO-BACKPROP")
    app.setDesktopFileName("ISAT")
    icon = QtGui.QIcon(str(Path(__file__).with_name("yolo-backprop-transparent.svg")))
    app.setWindowIcon(icon)
    mainwindow = MainWindow()
    mainwindow.setWindowIcon(icon)
    mainwindow.setWindowTitle("YOLO-BACKPROP")
    mainwindow.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
