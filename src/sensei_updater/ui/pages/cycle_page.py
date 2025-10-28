from __future__ import annotations
from typing import Dict, Any, List

from PySide6.QtCore import Qt, QRect, QEasingCurve, QPropertyAnimation, QPoint
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem, QFrame

from ..widgets import Header, GlassCard
from ..async_utils import BusyOverlay, JobController, run_async


class StepItem(QFrame):
    def __init__(self, text: str):
        super().__init__()
        self.setFixedHeight(36)
        h = QHBoxLayout(self)
        h.setContentsMargins(12, 0, 12, 0)
        h.setSpacing(8)
        self.dot = QLabel("●")
        self.dot.setStyleSheet("color:#444;font-weight:900;")
        self.label = QLabel(text)
        self.label.setStyleSheet("color:#cfd6eb;")
        h.addWidget(self.dot)
        h.addWidget(self.label)
        h.addStretch()


class Stepper(QWidget):
    def __init__(self, steps: List[str]):
        super().__init__()
        self._steps: List[StepItem] = []
        self._marker = QFrame(self)
        self._marker.setStyleSheet("background:#FF9F1C;border-radius:6px;")
        self._marker.setGeometry(QRect(0, 0, 4, 24))
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        for s in steps:
            item = StepItem(s)
            self._steps.append(item)
            v.addWidget(item)
        v.addStretch(1)
        self._anim = QPropertyAnimation(self._marker, b"pos", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.setCurrent(0, instant=True)

    def setCurrent(self, idx: int, instant: bool = False):
        idx = max(0, min(idx, len(self._steps) - 1))
        for i, it in enumerate(self._steps):
            if i < idx:
                it.dot.setText("✓")
                it.dot.setStyleSheet("color:#6bd66b;font-weight:900;")
                it.label.setStyleSheet("color:#9fd3a9;")
            elif i == idx:
                it.dot.setText("●")
                it.dot.setStyleSheet("color:#FF9F1C;font-weight:900;")
                it.label.setStyleSheet("color:#FFE58A;font-weight:700;")
            else:
                it.dot.setText("●")
                it.dot.setStyleSheet("color:#444;font-weight:900;")
                it.label.setStyleSheet("color:#cfd6eb;")
        target_y = self._steps[idx].y() + (self._steps[idx].height() - 24) // 2
        dest = QPoint(0, target_y)
        if instant:
            self._marker.move(dest)
        else:
            self._anim.stop()
            self._anim.setStartValue(self._marker.pos())
            self._anim.setEndValue(dest)
            self._anim.start()


class CyclePage(QWidget):
    def __init__(self, app_service, driver_service, system_service, cfg):
        super().__init__()
        self.app = app_service
        self.drivers = driver_service
        self.system = system_service
        self.cfg = cfg

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(Header("Cycle"))

        wrap = GlassCard()
        flow = QHBoxLayout()
        flow.setSpacing(16)
        self.stepper = Stepper([
            "Prepare",
            "Scan Drivers",
            "Install Drivers",
            "Scan Apps",
            "Update Apps",
            "Cleanup",
            "Health Check",
            "Finish"
        ])
        flow.addWidget(self.stepper, 0)

        right = QVBoxLayout()
        right.setSpacing(8)
        self.status = QLabel("Ready")
        self.status.setObjectName("Chip")
        self.out = QListWidget()
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)
        self.btn_run = QPushButton("Run Full Cycle")
        self.btn_run.setObjectName("PrimaryButton")
        self.btn_rescan = QPushButton("Rescan Only")
        self.btn_rescan.setObjectName("PrimaryButton")
        ctrl.addWidget(self.btn_run)
        ctrl.addWidget(self.btn_rescan)
        ctrl.addStretch(1)
        right.addWidget(self.status)
        right.addWidget(self.out, 1)
        right.addLayout(ctrl)
        flow.addLayout(right, 1)
        wrap.v.addLayout(flow)

        pad = QVBoxLayout()
        pad.setContentsMargins(24, 24, 24, 24)
        pad.addWidget(wrap)
        root.addLayout(pad, 1)

        self.overlay = BusyOverlay(self, compact=True)
        self.jobs = JobController(self, self.overlay)

        self.btn_run.clicked.connect(self.run_all)
        self.btn_rescan.clicked.connect(self.scan_only)

    def _append(self, text: str):
        self.out.addItem(QListWidgetItem(text))
        self.out.scrollToBottom()

    def _bump(self, step_idx: int, msg: str, progress_emit, msg_emit, pval: int):
        self.stepper.setCurrent(step_idx, instant=False)
        msg_emit(msg)
        progress_emit(pval)

    def scan_only(self):
        def task(progress, message):
            res: Dict[str, Any] = {"drivers": [], "apps": [], "notes": []}
            d = self.cfg.get_defaults() or {}
            force = bool(d.get("force_refresh"))
            skip_store = bool(d.get("skip_store_scan", True))
            scan_to = int(d.get("scan_timeout_sec", 120))
            self._bump(0, "Preparing to scan…", progress, message, 5)
            try:
                self._bump(1, "Scanning drivers…", progress, message, 20)
                drv = self.drivers.list_available(timeout_sec=max(120, scan_to)) or []
            except Exception as e:
                drv = []
                res["notes"].append(f"drivers_scan_error: {e}")
            try:
                self._bump(3, "Scanning apps…", progress, message, 60)
                apps = self.app.list_upgrades_all(force_refresh=force, skip_store=skip_store, scan_timeout=max(180, scan_to)) or []
            except Exception as e:
                apps = []
                res["notes"].append(f"apps_scan_error: {e}")
            res["drivers"] = drv
            res["apps"] = apps
            self._bump(7, "Done", progress, message, 100)
            return res

        def done(res):
            self.out.clear()
            if isinstance(res, dict) and res.get("error"):
                self.status.setText("Scan error")
                self._append(f"Scan error: {res['error']}")
                return
            drv = res.get("drivers", [])
            apps = res.get("apps", [])
            self.status.setText(f"Drivers: {len(drv)}  Apps: {len(apps)}")
            self._append(f"Scan complete. Drivers={len(drv)} Apps={len(apps)}")
            for n in res.get("notes", []):
                self._append(f"Note: {n}")

        t, w = run_async(task)
        self.jobs.start(t, w, "Scanning…", [self.btn_run, self.btn_rescan], done, timeout_ms=300_000)

    def run_all(self):
        def task(progress, message):
            out: Dict[str, Any] = {
                "scanned": {"drivers": 0, "apps": 0},
                "drivers": {"installed": False, "reboot": False},
                "apps": {"updated": [], "reinstalled": [], "failed": [], "skipped": [], "store_skipped": []},
                "cleanup": {"ok": False},
                "health": {"ok": False},
                "notes": []
            }
            d = self.cfg.get_defaults() or {}
            force = bool(d.get("force_refresh"))
            skip_store = bool(d.get("skip_store_scan", True))
            scan_to = int(d.get("scan_timeout_sec", 180))
            self._bump(0, "Preparing…", progress, message, 5)
            try:
                self._bump(1, "Scanning drivers…", progress, message, 15)
                drv_rows = self.drivers.list_available(timeout_sec=max(180, scan_to)) or []
            except Exception as e:
                drv_rows = []
                out["notes"].append(f"drivers_scan_error: {e}")
            out["scanned"]["drivers"] = len(drv_rows)
            if drv_rows:
                try:
                    self._bump(2, "Installing drivers…", progress, message, 35)
                    ok, reboot = self.drivers.update_drivers()
                    out["drivers"]["installed"] = bool(ok)
                    out["drivers"]["reboot"] = bool(reboot)
                except Exception as e:
                    out["drivers"]["installed"] = False
                    out["notes"].append(f"drivers_install_error: {e}")
            self._bump(3, "Scanning apps…", progress, message, 55)
            try:
                app_rows = self.app.list_upgrades_all(force_refresh=force, skip_store=skip_store, scan_timeout=max(240, scan_to)) or []
            except Exception as e:
                app_rows = []
                out["notes"].append(f"apps_scan_error: {e}")
            out["scanned"]["apps"] = len(app_rows)
            if app_rows:
                try:
                    self._bump(4, "Updating apps…", progress, message, 75)
                    ids = [r.get("Id") for r in app_rows if r.get("Id")]
                    r = self.app.update_ids(ids)
                    for k in ("updated", "reinstalled", "failed", "skipped", "store_skipped"):
                        out["apps"][k] = list(r.get(k, []))
                except Exception as e:
                    out["notes"].append(f"apps_update_error: {e}")
            self._bump(5, "Cleaning up…", progress, message, 88)
            try:
                self.system.cleanup_temp()
                self.system.empty_recycle_bin()
                out["cleanup"]["ok"] = True
            except Exception as e:
                out["cleanup"]["ok"] = False
                out["notes"].append(f"cleanup_error: {e}")
            self._bump(6, "Health check…", progress, message, 94)
            try:
                self.system.dism_sfc()
                out["health"]["ok"] = True
            except Exception as e:
                out["health"]["ok"] = False
                out["notes"].append(f"health_error: {e}")
            try:
                if self.system.has_pending_reboot():
                    out["drivers"]["reboot"] = True or out["drivers"]["reboot"]
            except Exception:
                pass
            self._bump(7, "Finish", progress, message, 100)
            return out

        def done(res):
            self.out.clear()
            if isinstance(res, dict) and res.get("error"):
                self.status.setText("Cycle error")
                self._append(f"Cycle error: {res['error']}")
                return
            scanned = res.get("scanned", {})
            drv = res.get("drivers", {})
            apps = res.get("apps", {})
            cl = res.get("cleanup", {})
            hl = res.get("health", {})
            self.status.setText(f"Drivers {scanned.get('drivers',0)} | Apps {scanned.get('apps',0)}")
            self._append(f"Drivers: installed={drv.get('installed')} reboot_required={drv.get('reboot')}")
            self._append(f"Apps: +{len(apps.get('updated', []))} reinstalled={len(apps.get('reinstalled', []))} failed={len(apps.get('failed', []))}")
            if apps.get("failed"):
                self._append("Failed: " + ", ".join(apps["failed"]))
            self._append(f"Cleanup: {'OK' if cl.get('ok') else 'Skipped/Failed'}")
            self._append(f"Health: {'OK' if hl.get('ok') else 'Skipped/Failed'}")
            for n in res.get("notes", []):
                self._append(f"Note: {n}")
            if drv.get("reboot"):
                self._append("A reboot is recommended.")

        t, w = run_async(task)
        self.jobs.start(t, w, "Running full cycle…", [self.btn_run, self.btn_rescan], done, timeout_ms=1_200_000)