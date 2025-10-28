from pathlib import Path
from importlib import resources
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStyle, QMessageBox
from .widgets import Sidebar, PageStack, Header, GlassCard, MetricTile, ResponsiveGrid, std_icon
from .pages.cycle_page import CyclePage
from .pages.apps_page import Apps
from .pages.drivers_page import Drivers
from .pages.settings_page import SettingsPage
from .pages.schedule_page import SchedulePage
from .pages.reports_page import ReportsPage
from ..core.admin import is_admin, run_as_admin

def _sanitize_qss(text: str) -> str:
    return text.replace("text-visible", "qproperty-textVisible")

class TitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("Header")
        self._press_pos = None
        h = QHBoxLayout(self); h.setContentsMargins(8, 4, 8, 4); h.setSpacing(6)
        self.title = QLabel("Sensei Updater")
        self.title.setStyleSheet("color:#FFE066;font-size:14px;font-weight:700")
        self.btn_admin = QPushButton("Admin"); self.btn_admin.setObjectName("PrimaryButton")
        self.btn_min = QPushButton(); self.btn_min.setFixedSize(QSize(32, 26)); self.btn_min.setIcon(std_icon(QStyle.SP_TitleBarMinButton)); self.btn_min.setIconSize(QSize(18,18))
        self.btn_max = QPushButton(); self.btn_max.setFixedSize(QSize(32, 26)); self.btn_max.setIcon(std_icon(QStyle.SP_TitleBarMaxButton)); self.btn_max.setIconSize(QSize(18,18))
        self.btn_close = QPushButton(); self.btn_close.setFixedSize(QSize(32, 26)); self.btn_close.setIcon(std_icon(QStyle.SP_TitleBarCloseButton)); self.btn_close.setIconSize(QSize(18,18))
        for b in (self.btn_min, self.btn_max, self.btn_close):
            b.setObjectName("TitleBtn")
        h.addWidget(self.title, 1)
        h.addWidget(self.btn_admin)
        h.addWidget(self.btn_min)
        h.addWidget(self.btn_max)
        h.addWidget(self.btn_close)
        self.btn_min.clicked.connect(self._on_min)
        self.btn_max.clicked.connect(self._on_max)
        self.btn_close.clicked.connect(self._on_close)
        self.btn_admin.clicked.connect(self._on_admin)

    def _on_admin(self):
        if is_admin():
            m = QMessageBox(self); m.setWindowTitle("Admin"); m.setText("Already running as Administrator."); m.exec(); return
        run_as_admin()

    def _on_min(self): self.window().showMinimized()
    def _on_max(self):
        w = self.window()
        w.showNormal() if w.isMaximized() else w.showMaximized()
    def _on_close(self): self.window().close()
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press_pos = e.globalPosition().toPoint()
            self._press_frame = self.window().frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if self._press_pos is not None and not self.window().isMaximized():
            delta = e.globalPosition().toPoint() - self._press_pos
            self.window().move(self._press_frame + delta)
    def mouseReleaseEvent(self, e): self._press_pos = None
    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton: self._on_max()

class Dashboard(QWidget):
    def __init__(self, version_text, reboot_text, goto_apps, goto_drivers, goto_reports, start_cycle):
        super().__init__()
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(Header("Dashboard"))
        grid = ResponsiveGrid()
        grid.add(MetricTile("Version", version_text))
        grid.add(MetricTile("Pending Reboot", reboot_text))
        grid.add(MetricTile("Privileges", "Admin" if is_admin() else "User"))
        c = GlassCard()
        h = QHBoxLayout(); h.setSpacing(12)
        b_apps = QPushButton("Scan Apps");    b_apps.setIcon(std_icon(QStyle.SP_BrowserReload))
        b_drv  = QPushButton("Scan Drivers"); b_drv.setIcon(std_icon(QStyle.SP_BrowserReload))
        b_rep  = QPushButton("View Reports"); b_rep.setIcon(std_icon(QStyle.SP_FileDialogDetailedView))
        for b in (b_apps, b_drv, b_rep):
            b.setObjectName("PrimaryButton"); h.addWidget(b)
        c.v.addLayout(h)
        b_apps.clicked.connect(goto_apps); b_drv.clicked.connect(goto_drivers); b_rep.clicked.connect(goto_reports)
        grid.add(c)
        hero = GlassCard(); hero.v.setSpacing(16)
        big = QPushButton("Start"); big.setFixedSize(160, 160)
        big.setIcon(std_icon(QStyle.SP_MediaPlay)); big.setIconSize(big.size() * 0.5)
        big.setStyleSheet("background:#FF7F11;color:#111;border-radius:80px;font-size:22px;font-weight:800;border:1px solid #FF9F1C")
        big.clicked.connect(start_cycle)
        wrap = QWidget(); wv = QVBoxLayout(wrap); wv.setAlignment(Qt.AlignCenter); wv.addWidget(big)
        hero.v.addWidget(QLabel("Complete Cycle"))
        hero.v.addWidget(wrap)
        grid.add(hero)
        v.addWidget(grid)

class MainWindow(QMainWindow):
    def __init__(self, console, app, drivers, system, cfg, sched, reports, version_text):
        super().__init__()
        self.console, self.app, self.drivers, self.system = console, app, drivers, system
        self.cfg, self.sched, self.reports = cfg, sched, reports
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowTitle("Sensei Updater")
        self.resize(1220, 760)

        root = QWidget(); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0)
        self.titlebar = TitleBar(self); outer.addWidget(self.titlebar)
        body = QWidget(); outer.addWidget(body, 1)
        h = QHBoxLayout(body); h.setContentsMargins(0, 0, 0, 0)
        self.sidebar = Sidebar(); self.pages = PageStack()

        reboot = "Yes" if self._safe_pending_reboot() else "No"
        dash = QWidget(); dv = QVBoxLayout(dash); dv.setContentsMargins(0, 0, 0, 0)
        cycle_page = CyclePage(app, drivers, system, cfg); self._cycle_page = cycle_page
        d_hdr = Dashboard(version_text, reboot, self.goto_apps, self.goto_drivers, self.goto_reports, self.start_cycle)
        dv.addWidget(d_hdr)

        apps = Apps(app)
        drivers_w = Drivers(drivers)
        reports_w = ReportsPage(cfg)
        settings_w = SettingsPage(cfg, sched, app)
        sched_w = SchedulePage(cfg, sched)

        for w in (dash, apps, drivers_w, cycle_page, sched_w, reports_w, settings_w):
            self.pages.addWidget(w)

        self.btn_dash     = self.sidebar.add("Dashboard", self.goto_dash, True)
        self.btn_apps     = self.sidebar.add("Apps", self.goto_apps)
        self.btn_drivers  = self.sidebar.add("Drivers", self.goto_drivers)
        self.btn_cycle    = self.sidebar.add("Cycle", self.goto_cycle)
        self.btn_schedule = self.sidebar.add("Schedule", self.goto_schedule)
        self.btn_reports  = self.sidebar.add("Reports", self.goto_reports)
        self.btn_settings = self.sidebar.add("Settings", self.goto_settings)

        h.addWidget(self.sidebar); h.addWidget(self.pages, 1)
        QTimer.singleShot(10, lambda: self.pages.setCurrentIndexAnimated(0))

        try: self.app.check_environment()
        except Exception: pass

    def _sel(self, idx, btn):
        self.sidebar.select(btn); self.pages.setCurrentIndexAnimated(idx)
    def goto_dash(self):     self._sel(0, self.btn_dash)
    def goto_apps(self):     self._sel(1, self.btn_apps)
    def goto_drivers(self):  self._sel(2, self.btn_drivers)
    def goto_cycle(self):    self._sel(3, self.btn_cycle)
    def goto_schedule(self): self._sel(4, self.btn_schedule)
    def goto_reports(self):  self._sel(5, self.btn_reports)
    def goto_settings(self): self._sel(6, self.btn_settings)
    def start_cycle(self):   self.goto_cycle(); self._cycle_page.run_all()
    def _safe_pending_reboot(self):
        try: return self.system.has_pending_reboot()
        except Exception: return False

def _load_qss_text(qss_path: str | None):
    if qss_path:
        p = Path(qss_path)
        if p.exists():
            try:
                return p.read_text(encoding="utf-8")
            except Exception:
                pass

    try:
        with resources.as_file(resources.files("sensei_updater.ui").joinpath("styles.qss")) as p:
            if p.exists():
                return p.read_text(encoding="utf-8")
    except Exception:
        pass

    try:
        local = Path(__file__).with_name("styles.qss")
        if local.exists():
            return local.read_text(encoding="utf-8")
    except Exception:
        pass

    return ""

def _install_exception_guard():
    import sys, traceback
    def guard_hook(exc_type, exc, tb):
        try:    msg = "".join(traceback.format_exception(exc_type, exc, tb))[-3000:]
        except Exception: msg = str(exc) or "Unhandled error"
        try:
            if QApplication.instance() is None:
                print(msg); return
            m = QMessageBox(); m.setWindowTitle("Error")
            m.setText("An unexpected error occurred.")
            m.setDetailedText(msg); m.exec()
        except Exception: pass
    sys.excepthook = guard_hook

def start_gui(console, app, drivers, system, cfg, sched, reports, version_text, qss_path=None):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    a = QApplication.instance() or QApplication([])
    _install_exception_guard()
    qss = _load_qss_text(qss_path)
    if qss: a.setStyleSheet(_sanitize_qss(qss))
    w = MainWindow(console, app, drivers, system, cfg, sched, reports, version_text)
    w.show()
    return a.exec()