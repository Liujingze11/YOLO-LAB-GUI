"""Shared native glass materials; no opacity effects on image or text content."""
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets


LIGHT = {
    'bg': 'transparent', 'card_bg': 'rgba(255, 255, 255, 178)',
    'text': '#1d1d1f', 'text_secondary': '#6e6e73', 'text_muted': '#86868b',
    'border': 'rgba(0, 0, 0, 24)', 'border_hover': 'rgba(0, 0, 0, 48)',
    'accent': '#007aff', 'accent_hover': '#1987ff', 'accent_pressed': '#0066d6',
    'secondary_bg': 'rgba(255, 255, 255, 160)',
    'secondary_hover': 'rgba(255, 255, 255, 225)', 'secondary_pressed': 'rgba(232, 232, 232, 210)',
    'danger': '#ef5a61', 'danger_hover': '#fa7177', 'danger_pressed': '#d8454c',
    'disabled': 'rgba(142, 142, 147, 90)',
    'log_bg': 'rgba(248, 248, 248, 225)', 'log_text': '#1d1d1f', 'log_selection': '#dedee3',
    'progress_track': 'rgba(142, 142, 147, 35)',
}
DARK = {
    'bg': 'transparent', 'card_bg': 'rgba(48, 48, 50, 205)',
    'text': '#f5f5f7', 'text_secondary': '#b7b7bd', 'text_muted': '#98989d',
    'border': 'rgba(255, 255, 255, 36)', 'border_hover': 'rgba(255, 255, 255, 70)',
    'accent': '#5bacff', 'accent_hover': '#7bbcff', 'accent_pressed': '#3d92ed',
    'secondary_bg': 'rgba(110, 110, 115, 90)',
    'secondary_hover': 'rgba(145, 145, 150, 105)', 'secondary_pressed': 'rgba(90, 90, 95, 170)',
    'danger': '#ef6b72', 'danger_hover': '#ff848a', 'danger_pressed': '#d7505a',
    'disabled': 'rgba(115, 115, 120, 95)',
    'log_bg': 'rgba(24, 24, 26, 235)', 'log_text': '#f5f5f7', 'log_selection': '#48484a',
    'progress_track': 'rgba(200, 200, 205, 28)',
}


def surface(dark=False):
    if dark:
        return 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(62, 62, 64, 216), stop:1 rgba(42, 42, 44, 182))'
    return 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(255, 255, 255, 222), stop:1 rgba(250, 250, 250, 180))'


def page_style(name, dark=False):
    background = ('qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1c1c1e, stop:0.55 #242426, stop:1 #29292b)'
                  if dark else 'transparent')
    color = DARK['text'] if dark else LIGHT['text']
    result = 'QWidget#%s { background: %s; } QWidget { color: %s; } QLabel { background: transparent; }' % (name, background, color)
    if dark:
        result += 'QPushButton, QComboBox { background: rgba(90,90,95,170); color: #f5f5f7; border-color: rgba(255,255,255,36); }'
        result += 'QFrame[glassRole="commandBar"] { background: ' + surface(True) + '; border-color: rgba(255,255,255,36); }'
        result += arrow_styles(True)
    return result


def arrow_styles(dark=False):
    directory = Path(__file__).parent / 'ui' / 'theme'
    suffix = '-dark' if dark else ''
    up, down = (str(directory / ('chevron-' + direction + suffix + '.svg')) for direction in ('up', 'down'))
    return '''
    QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right;
        width: 16px; border: none; background: transparent; }
    QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right;
        width: 16px; border: none; background: transparent; }
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url("%s"); width: 8px; height: 5px; }
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QComboBox::down-arrow { image: url("%s"); width: 8px; height: 5px; }
    ''' % (up, down)


def widget_stylesheet(dark=False):
    sheet = '''
    QWidget { color: #1d1d1f; font-family: "Noto Sans CJK SC";
              selection-background-color: #d4e7ff; selection-color: #1d1d1f; }
    QMainWindow#isatAnnotationWorkspace QWidget, QWidget#DataScreening QWidget,
    QWidget#ModelDevelopment QWidget { font-size: 14px; }
    QMainWindow#MainWindow { background: #f5f5f5; }
    QMainWindow#isatAnnotationWorkspace, QStackedWidget, QWidget#centralwidget,
    QWidget#DataScreening, QWidget#WorkbenchFrame { background: transparent; border: none; }
    QFrame#WorkbenchHeader, QFrame[glassRole="commandBar"] {
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(255,255,255,240),stop:1 rgba(255,255,255,170));
        border: 1px solid rgba(255,255,255,245); border-radius: 14px; }
    QLabel#WorkbenchTitle { font-size: 21px; font-weight: 600; color: #1d1d1f; }
    QLabel#WorkbenchProject { color: #6e6e73; font-size: 13px; }
    QLabel { background: transparent; }
    QLabel[glassRole="muted"] { color: #6e6e73; }
    QDialog { background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                 stop:0 #fafafa, stop:0.55 #f5f5f5, stop:1 #eeeeee); }
    QToolBar { background: rgba(255,255,255,180); border: none; spacing: 3px; padding: 4px; }
    QToolBar::separator { background: rgba(0,0,0,24); width: 1px; height: 1px; margin: 6px; }
    QToolBar#isatModelDevelopmentNavigation {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(255,255,255,220), stop:1 rgba(245,245,245,135));
        border-right: 1px solid rgba(255,255,255,225); spacing: 5px; padding: 12px 6px; }
    QToolButton { background: transparent; border: 1px solid transparent; border-radius: 7px; }
    QToolButton:hover { background: rgba(255,255,255,195); border-color: rgba(0,0,0,28); }
    QToolButton:checked, QToolButton:pressed { background: rgba(225,225,225,160); border-color: rgba(0,0,0,36); }
    QToolButton:disabled { color: #98989d; }
    QToolBar#isatModelDevelopmentNavigation QToolButton { font-size: 12px; border-radius: 14px; color: #6e6e73; padding: 4px; }
    QToolBar#isatModelDevelopmentNavigation QToolButton:checked {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255,255,255,245), stop:1 rgba(242,242,242,200));
        border: 1px solid rgba(255,255,255,255); color: #007aff; }
    QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                     stop:0 rgba(255,255,255,240), stop:1 rgba(248,248,248,155));
        border: 1px solid rgba(0,0,0,25); border-radius: 9px; padding: 6px 12px; }
    QPushButton:hover { background: rgba(255,255,255,250); border-color: rgba(0,0,0,60); }
    QPushButton:pressed { background: rgba(230,230,230,210); }
    QPushButton:default, QPushButton[glassRole="primary"] {
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1987ff,stop:1 #007aff);
        color: white; border: 1px solid rgba(0,100,220,140); }
    QPushButton:default:hover, QPushButton[glassRole="primary"]:hover { background: #1987ff; }
    QPushButton:disabled { color: #98989d; background: rgba(248,248,248,95); border-color: rgba(0,0,0,18); }
    QPushButton:focus, QToolButton:focus { border-color: #007aff; }
    QWidget#DataScreening QPushButton { min-width: 62px; }
    QWidget#ScreeningTrashPanel { background: rgba(255,255,255,155); border: 1px solid rgba(0,0,0,22); border-radius: 12px; }
    QListWidget#ScreeningTrashStrip { background: transparent; border: none; }
    QMainWindow#isatAnnotationWorkspace QPushButton { padding: 5px 6px; }
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
        background: rgba(255,255,255,185); border: 1px solid rgba(0,0,0,32);
        border-radius: 8px; padding: 5px 8px; }
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: #007aff; background: rgba(255,255,255,235); }
    QComboBox::drop-down { border: none; width: 20px; }
    QAbstractItemView, QTextEdit, QPlainTextEdit {
        background: rgba(255,255,255,235); border: 1px solid rgba(0,0,0,18);
        border-radius: 12px; outline: none; }
    QAbstractItemView::item:selected { background: rgba(181,215,255,160); color: #1d1d1f; }
    QAbstractItemView::item:hover { background: rgba(230,230,230,130); }
    QComboBox QAbstractItemView { background: #fafafa; border: 1px solid #d9d9dc; }
    QGraphicsView { background: #f2f2f4; border: 1px solid rgba(0,0,0,18); border-radius: 12px; }
    QScrollArea { background: transparent; border: none; }
    QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
    QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
    QScrollBar::handle { background: rgba(110,110,115,90); border-radius: 4px; min-height: 24px; min-width: 24px; }
    QScrollBar::handle:hover { background: rgba(100,100,105,145); }
    QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
    QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
    QMenuBar { background: rgba(255,255,255,135); border: none; }
    QMenuBar::item { background: transparent; padding: 5px 9px; border-radius: 7px; }
    QMenuBar::item:selected { background: rgba(201,225,255,160); }
    QMenu { background: #f7f7f7; border: 1px solid #dcdcdf; border-radius: 10px; padding: 5px; }
    QMenu::item { padding: 5px 24px; border-radius: 6px; }
    QMenu::item:selected { background: #d8eaff; color: #1d1d1f; }
    QMenu::item:disabled { color: #98989d; }
    QMenu::separator { height: 1px; background: #dcdcdf; margin: 4px 8px; }
    QDockWidget { background: rgba(255,255,255,200); border: none; }
    QDockWidget::title { background: rgba(255,255,255,210); border-radius: 8px; padding: 7px; font-weight: 500; }
    QMainWindow::separator { background: rgba(255,255,255,150); width: 6px; height: 6px; }
    QMainWindow::separator:hover, QSplitter::handle:hover { background: rgba(140,140,145,95); }
    QSplitter::handle { background: rgba(255,255,255,65); }
    QStatusBar { background: rgba(255,255,255,120); color: #6e6e73; }
    QStatusBar::item { border: none; }
    QGroupBox { border: 1px solid rgba(255,255,255,210); border-radius: 10px; margin-top: 10px; background: rgba(255,255,255,100); }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; color: #6e6e73; }
    QHeaderView::section { background: #efeff0; border: none; border-bottom: 1px solid #d9d9dc; padding: 4px; }
    QProgressBar { background: rgba(142,142,147,40); border: none; border-radius: 6px; text-align: center; }
    QProgressBar::chunk { background: #007aff; border-radius: 6px; }
    QToolTip { background: #fafafa; color: #1d1d1f; border: 1px solid #d4d4d7; padding: 5px; }
    ''' + arrow_styles(dark)
    return sheet + (_dark_widget_stylesheet() if dark else '')


def _dark_widget_stylesheet():
    """Native annotation and screening use the same dark materials as models."""
    return '''
    QWidget { color: #f5f5f7; selection-background-color: #355579; selection-color: #ffffff; }
    QMainWindow#MainWindow, QDialog { background: #242426; }
    QLabel#WorkbenchTitle { color: #f5f5f7; }
    QLabel#WorkbenchProject, QLabel[glassRole="muted"] { color: #b7b7bd; }
    QFrame#WorkbenchHeader, QFrame[glassRole="commandBar"] {
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(62,62,64,225),stop:1 rgba(44,44,46,185));
        border-color: rgba(255,255,255,30); }
    QToolBar, QMenuBar, QStatusBar { background: rgba(44,44,46,220); }
    QToolBar#isatModelDevelopmentNavigation { background: rgba(44,44,46,180); border-color: rgba(255,255,255,25); }
    QToolBar#isatModelDevelopmentNavigation QToolButton { color: #b7b7bd; }
    QToolBar#isatModelDevelopmentNavigation QToolButton:checked { color: #5bacff; background: rgba(90,90,94,140); border-color: rgba(255,255,255,35); }
    QToolButton:hover, QToolButton:checked, QToolButton:pressed { background: rgba(100,100,105,100); border-color: rgba(255,255,255,30); }
    QPushButton { color: #f5f5f7; background: rgba(75,75,78,190); border-color: rgba(255,255,255,30); }
    QPushButton:hover { background: rgba(95,95,100,210); border-color: rgba(255,255,255,60); }
    QPushButton:pressed { background: #48484a; }
    QPushButton:default, QPushButton[glassRole="primary"] { background: #007aff; color: white; }
    QPushButton:disabled { background: rgba(70,70,74,100); color: #98989d; border-color: rgba(255,255,255,18); }
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: rgba(48,48,50,230); color: #f5f5f7; border-color: rgba(255,255,255,36); }
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { background: #3a3a3c; border-color: #5bacff; }
    QAbstractItemView, QTextEdit, QPlainTextEdit { background: rgba(40,40,42,240); color: #f5f5f7; border-color: rgba(255,255,255,25); }
    QAbstractItemView::item:selected { background: #355579; color: #ffffff; }
    QAbstractItemView::item:hover { background: rgba(100,100,105,90); }
    QComboBox QAbstractItemView { background: #303032; border-color: #48484a; color: #f5f5f7; }
    QGraphicsView { background: #28282a; border-color: rgba(255,255,255,25); }
    QWidget#ScreeningTrashPanel { background: rgba(48,48,50,200); border-color: rgba(255,255,255,25); }
    QListWidget#ScreeningTrashStrip { background: transparent; border: none; }
    QMenu { background: #303032; color: #f5f5f7; border-color: #48484a; }
    QMenu::item:selected, QMenuBar::item:selected { background: #355579; color: #ffffff; }
    QMenu::separator, QToolBar::separator { background: rgba(255,255,255,30); }
    QDockWidget { background: rgba(44,44,46,180); }
    QDockWidget::title { background: rgba(55,55,58,200); color: #f5f5f7; }
    QMainWindow::separator, QSplitter::handle { background: rgba(44,44,46,120); }
    QGroupBox { background: rgba(48,48,50,180); border-color: rgba(255,255,255,30); }
    QGroupBox::title { color: #b7b7bd; }
    QHeaderView::section { background: #3a3a3c; color: #f5f5f7; border-color: #48484a; }
    QToolTip { background: #3a3a3c; color: #f5f5f7; border-color: #636366; }
    QTabBar::tab { background: #303032; color: #b7b7bd; }
    QTabBar::tab:selected { background: #48484a; color: #ffffff; }
    QTabWidget::pane { background: #28282a; border: 1px solid rgba(255,255,255,25); }
    '''


class GlassBackdrop(QtWidgets.QWidget):
    """Neutral gray light behind translucent widgets."""
    def __init__(self, parent):
        super().__init__(parent)
        self.dark = False
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        parent.installEventFilter(self)
        self.setGeometry(parent.rect()); self.show(); self.lower()

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.Resize:
            self.setGeometry(watched.rect())
        return False

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        background = QtGui.QLinearGradient(0, 0, self.width(), self.height())
        background.setColorAt(0, QtGui.QColor('#1c1c1e' if self.dark else '#fafafa'))
        background.setColorAt(.5, QtGui.QColor('#242426' if self.dark else '#f5f5f5'))
        background.setColorAt(1, QtGui.QColor('#29292b' if self.dark else '#ededed'))
        painter.fillRect(self.rect(), background)


def navigation_icon(kind, dark=False):
    icon = QtGui.QIcon()
    palette = DARK if dark else LIGHT
    for state, color in ((QtGui.QIcon.Off, palette['text_secondary']), (QtGui.QIcon.On, palette['accent'])):
        for scale in (1, 2, 3):
            pixmap = QtGui.QPixmap(24 * scale, 24 * scale); pixmap.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(pixmap); painter.scale(scale, scale)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setPen(QtGui.QPen(QtGui.QColor(color), 1.6, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
            if kind == 'home':
                painter.drawRoundedRect(QtCore.QRectF(3, 3, 18, 18), 6, 6)
                painter.drawLine(16, 12, 8, 12); painter.drawLine(8, 12, 12, 8); painter.drawLine(8, 12, 12, 16)
            elif kind == 'screening':
                for x in (3, 14):
                    for y in (3, 14): painter.drawRoundedRect(QtCore.QRectF(x, y, 7, 7), 2, 2)
            elif kind == 'annotation':
                painter.drawRoundedRect(QtCore.QRectF(4, 4, 16, 16), 4, 4)
                painter.drawLine(8, 16, 16, 8); painter.drawLine(8, 16, 12, 15)
                painter.drawLine(8, 16, 9, 12); painter.drawLine(14, 8, 16, 10)
            else:
                painter.drawRoundedRect(QtCore.QRectF(6, 6, 12, 12), 3, 3)
                painter.drawRoundedRect(QtCore.QRectF(9, 9, 6, 6), 1, 1)
                for n in (9, 15):
                    painter.drawLine(n, 2, n, 5); painter.drawLine(n, 19, n, 22)
                    painter.drawLine(2, n, 5, n); painter.drawLine(19, n, 22, n)
            painter.end(); pixmap.setDevicePixelRatio(scale)
            icon.addPixmap(pixmap, QtGui.QIcon.Normal, state)
    return icon


def install_window_theme(window):
    window._glass_backdrop = GlassBackdrop(window)
    navigation = window.model_development.navigation
    navigation.setMinimumWidth(96)
    for action in navigation.actions():
        button = navigation.widgetForAction(action)
        if isinstance(button, QtWidgets.QToolButton):
            button.setMinimumWidth(80)
            button.setFixedHeight(64)
    for widget in [window] + window.findChildren(QtWidgets.QWidget):
        font = widget.font(); font.setFamily('Noto Sans CJK SC'); widget.setFont(font)
    apply_window_theme(window, False)


def apply_window_theme(window, dark=False):
    window.setProperty('darkMode', dark)
    window.setStyleSheet(widget_stylesheet(dark))
    window._glass_backdrop.dark = dark
    window._glass_backdrop.update()
    controller = window.model_development
    for kind in ('home', 'screening', 'annotation', 'development'):
        getattr(controller, kind + '_action').setIcon(navigation_icon(kind, dark))
    palette = window.palette()
    palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Text, QtGui.QColor('#86868b'))
    window.setPalette(palette)
    window._glass_backdrop.lower()
