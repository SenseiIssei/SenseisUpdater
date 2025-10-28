from __future__ import annotations
from typing import List, Dict, Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem
from ..widgets import Header, GlassCard
from ..async_utils import BusyOverlay, JobController, run_async

class Apps(QWidget):
    def __init__(self, app_service):
        super().__init__()
        self.app = app_service
        self._rows: List[Dict[str, Any]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(Header("Applications"))

        card = GlassCard()
        top = QHBoxLayout()
        top.setSpacing(8)
        self.btn_scan = QPushButton("Scan")
        self.btn_scan.setObjectName("PrimaryButton")
        self.btn_update_sel = QPushButton("Update Selected")
        self.btn_update_sel.setObjectName("PrimaryButton")
        self.btn_update_all = QPushButton("Update All")
        self.btn_update_all.setObjectName("PrimaryButton")
        top.addWidget(self.btn_scan)
        top.addWidget(self.btn_update_sel)
        top.addWidget(self.btn_update_all)
        top.addStretch(1)

        self.msg = QLabel("")
        self.msg.setObjectName("Chip")

        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.ExtendedSelection)
        self.list.setAlternatingRowColors(True)

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
        self.btn_update_all.clicked.connect(self.update_all)
        self.btn_update_sel.clicked.connect(self.update_selected)

    def _populate(self, rows: List[Dict[str, Any]]):
        self.list.clear()
        self._rows = rows or []
        if not rows:
            it = QListWidgetItem("No updatable apps found")
            it.setFlags(Qt.NoItemFlags)
            self.list.addItem(it)
            self.msg.setText("No updates")
            return
        for r in rows:
            name = r.get("Name") or r.get("Id")
            pid = r.get("Id", "")
            src = r.get("Source", "")
            ver = r.get("Version", "")
            avail = r.get("Available", "")
            item = QListWidgetItem(f"{name}  ({pid})  {ver} → {avail}   [{src}]")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.list.addItem(item)
        self.msg.setText(f"Found {len(rows)} app updates")

    def scan(self):
        self.msg.setText("")
        def task(progress, message):
            message("Scanning applications…")
            d = getattr(self.app, "cfg", None) and self.app.cfg.get_defaults() or {}
            force = bool(d.get("force_refresh"))
            skip_store = bool(d.get("skip_store_scan", True))
            scan_to = int(d.get("scan_timeout_sec", 120))
            try:
                rows = self.app.list_upgrades_all(force_refresh=force, skip_store=skip_store, scan_timeout=max(90, scan_to)) or []
            except Exception as e:
                return {"error": str(e)}
            return rows
        def done(res):
            if isinstance(res, dict) and res.get("error"):
                self._populate([])
                self.list.addItem(QListWidgetItem(f"Scan error: {res['error']}"))
                self.msg.setText(f"Scan error: {res['error']}")
                return
            self._populate(res)
        t, w = run_async(task)
        self.jobs.start(t, w, "Scanning applications…", [self.btn_scan, self.btn_update_all, self.btn_update_sel], done, timeout_ms=180_000)

    def _selected_ids(self) -> List[str]:
        ids: List[str] = []
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it and it.checkState() == Qt.Checked:
                text = it.text()
                pid = ""
                for r in self._rows:
                    nm = r.get("Name") or r.get("Id")
                    if nm and nm in text and r.get("Id"):
                        pid = r["Id"]
                        break
                if pid:
                    ids.append(pid)
        return ids

    def update_all(self):
        ids = [r.get("Id") for r in self._rows if r.get("Id")]
        self._run_update(ids, "Updating all…")

    def update_selected(self):
        ids = self._selected_ids()
        self._run_update(ids, "Updating selected…")

    def _run_update(self, ids: List[str], label: str):
        def task(progress, message):
            if not ids:
                return {"updated": [], "reinstalled": [], "failed": [], "skipped": [], "store_skipped": []}
            message("Updating applications…")
            try:
                r = self.app.update_ids(ids)
            except Exception as e:
                return {"error": str(e)}
            return r
        def done(res):
            if isinstance(res, dict) and res.get("error"):
                self.msg.setText(f"Update error: {res['error']}")
                self.list.addItem(QListWidgetItem(f"Update error: {res['error']}"))
                return
            upd = len(res.get("updated", []))
            rei = len(res.get("reinstalled", []))
            fail = len(res.get("failed", []))
            self.msg.setText(f"Finished (+{upd} reinstalled={rei} failed={fail})")
            self.list.addItem(QListWidgetItem(f"Update finished: +{upd} reinstalled={rei} failed={fail}"))
            self.scan()
        t, w = run_async(task)
        self.jobs.start(t, w, label, [self.btn_scan, self.btn_update_all, self.btn_update_sel], done, timeout_ms=30 * 60_000)