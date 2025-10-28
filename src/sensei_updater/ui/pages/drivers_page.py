from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem

from ..widgets import Header, GlassCard
from ..async_utils import BusyOverlay, JobController, run_async
from ...core.admin import is_admin


class Drivers(QWidget):
    def __init__(self, driver_service):
        super().__init__()
        self.drivers = driver_service

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(Header("Drivers"))

        card = GlassCard()
        top = QHBoxLayout()
        top.setSpacing(8)
        self.btn_scan = QPushButton("Scan")
        self.btn_scan.setObjectName("PrimaryButton")
        self.btn_install_sel = QPushButton("Install Selected")
        self.btn_install_sel.setObjectName("PrimaryButton")
        self.btn_install_all = QPushButton("Install All")
        self.btn_install_all.setObjectName("PrimaryButton")
        top.addWidget(self.btn_scan)
        top.addWidget(self.btn_install_sel)
        top.addWidget(self.btn_install_all)
        top.addStretch(1)

        self.msg = QLabel("")
        self.msg.setObjectName("Chip")

        self.list = QListWidget()

        card.v.addLayout(top)
        card.v.addWidget(self.msg)
        card.v.addWidget(self.list)

        outer = QVBoxLayout()
        outer.setContentsMargins(24, 24, 24, 24)
        outer.addWidget(card)

        root.addLayout(outer)

        self.overlay = BusyOverlay(self, compact=True)
        self.jobs = JobController(self, self.overlay)

        self.btn_scan.clicked.connect(self.scan)
        self.btn_install_all.clicked.connect(self.install_all)
        self.btn_install_sel.clicked.connect(self.install_selected)

    def _populate(self, rows):
        self.list.clear()
        if not rows:
            self.list.addItem(QListWidgetItem("No driver updates found."))
            self.msg.setText("No updates")
            return
        for r in rows:
            kb = r.get("kb") or ""
            title = r.get("title") or ""
            text = (f"{kb}  {title}").strip()
            it = QListWidgetItem(text)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Unchecked)
            self.list.addItem(it)
        self.msg.setText(f"Found {len(rows)} driver updates")

    def scan(self):
        self.msg.setText("")
        def task(progress, message):
            message("Scanning drivers…")
            try:
                rows = self.drivers.list_available(timeout_sec=300) or []
            except Exception as e:
                return {"error": str(e)}
            return rows

        def done(res):
            if isinstance(res, dict) and res.get("error"):
                self._populate([])
                self.list.addItem(QListWidgetItem(f"Scan error: {res['error']}"))
                return
            self._populate(res)

        t, w = run_async(task)
        self.jobs.start(t, w, "Scanning drivers…",
                        [self.btn_scan, self.btn_install_all, self.btn_install_sel],
                        done,
                        timeout_ms=300_000)

    def _selected_kbs(self):
        kbs = []
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it and it.checkState() == Qt.Checked:
                kb = (it.text() or "").split("  ")[0].strip()
                if kb:
                    kbs.append(kb)
        return kbs

    def install_selected(self):
        if not is_admin():
            self.msg.setText("Administrator required for driver installation")
            return
        kbs = self._selected_kbs()
        if not kbs:
            self.msg.setText("No items selected")
            return

        def task(progress, message):
            message("Installing selected drivers…")
            try:
                ok, reboot = self.drivers.install_kbs(kbs)
            except Exception as e:
                return {"error": str(e)}
            return {"ok": ok, "reboot": reboot}

        def done(res):
            if isinstance(res, dict) and res.get("error"):
                self.msg.setText(f"Failed: {res['error']}")
                return
            self.msg.setText("Reboot required" if res.get("reboot") else ("Done" if res.get("ok") else "Failed"))
            self.scan()

        t, w = run_async(task)
        self.jobs.start(t, w, "Installing drivers…",
                        [self.btn_scan, self.btn_install_all, self.btn_install_sel],
                        done,
                        timeout_ms=15 * 60_000)

    def install_all(self):
        if not is_admin():
            self.msg.setText("Administrator required for driver installation")
            return

        def task(progress, message):
            message("Installing available drivers…")
            try:
                ok, reboot = self.drivers.update_drivers()
            except Exception as e:
                return {"error": str(e)}
            return {"ok": ok, "reboot": reboot}

        def done(res):
            if isinstance(res, dict) and res.get("error"):
                self.msg.setText(f"Failed: {res['error']}")
                return
            self.msg.setText("Reboot required" if res.get("reboot") else ("Done" if res.get("ok") else "Failed"))
            self.scan()

        t, w = run_async(task)
        self.jobs.start(t, w, "Installing drivers…",
                        [self.btn_scan, self.btn_install_all, self.btn_install_sel],
                        done,
                        timeout_ms=15 * 60_000)