import os
import json
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, QLabel, QTextEdit

from ..widgets import Header, GlassCard
from ..async_utils import BusyOverlay, JobController, run_async


def _expand_env(path_str: str) -> Path:
    try:
        return Path(os.path.expandvars(path_str)).expanduser()
    except Exception:
        return Path(path_str).expanduser()


class ReportsPage(QWidget):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self._items = []
        self._base_dir = self._resolve_base_dir()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(Header("Reports"))

        card = GlassCard()
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setObjectName("PrimaryButton")
        self.btn_open_dir = QPushButton("Open Folder")
        self.btn_open_dir.setObjectName("PrimaryButton")
        ctrl.addWidget(self.btn_refresh)
        ctrl.addWidget(self.btn_open_dir)
        ctrl.addStretch(1)
        card.v.addLayout(ctrl)

        body = QHBoxLayout()
        body.setSpacing(12)
        self.list = QListWidget()
        self.list.setMinimumWidth(320)
        self.view = QTextEdit()
        self.view.setReadOnly(True)
        body.addWidget(self.list, 0)
        body.addWidget(self.view, 1)
        card.v.addLayout(body, 1)

        pad = QVBoxLayout()
        pad.setContentsMargins(24, 24, 24, 24)
        pad.addWidget(card)
        root.addLayout(pad, 1)

        self.overlay = None
        self.jobs = None

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_open_dir.clicked.connect(self.open_dir)
        self.list.currentItemChanged.connect(self._on_select)

    def _resolve_base_dir(self) -> Path:
        d = self.cfg.get_defaults() or {}
        out = d.get("out") or r"%LOCALAPPDATA%\SenseiUpdater\last-run.json"
        out_path = _expand_env(out)
        return out_path.parent if out_path.suffix else out_path

    def _format_dt(self, ts: float) -> str:
        try:
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return "unknown time"

    def _pretty_json(self, raw: str) -> str:
        try:
            return json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
        except Exception:
            return raw

    def refresh(self):
        def task(progress, message):
            message("Scanning report folder…")
            progress(5)
            base = self._base_dir
            rows = []
            try:
                if base.exists() and base.is_dir():
                    for ext in ("*.json", "*.txt"):
                        for p in base.glob(ext):
                            try:
                                s = p.stat()
                                rows.append({"path": str(p), "size": int(s.st_size), "mtime": float(s.st_mtime)})
                            except Exception:
                                pass
                rows.sort(key=lambda r: r["mtime"], reverse=True)
            except Exception as e:
                return {"error": str(e)}
            progress(100)
            return rows

        def done(res):
            self._items = []
            self.list.clear()
            self.view.clear()

            if isinstance(res, dict) and res.get("error"):
                self.view.setPlainText(f"Could not scan reports:\n{res['error']}")
                return

            rows = res or []
            if not rows:
                self.view.setPlainText("No reports found.")
                return

            self._items = rows
            for it in rows:
                p = Path(it["path"])
                dt = self._format_dt(it["mtime"])
                sz = it["size"]
                self.list.addItem(QListWidgetItem(f"{p.name}   ({sz} bytes, {dt})"))

            if self.list.count() > 0:
                self.list.setCurrentRow(0)

        t, w = run_async(task)
        self.jobs.start(t, w, "Loading reports…", [self.btn_refresh, self.btn_open_dir], done, timeout_ms=120_000)

    def _on_select(self, cur: QListWidgetItem, prev: QListWidgetItem):
        idx = self.list.currentRow()
        if idx < 0 or idx >= len(self._items):
            self.view.clear()
            return
        path = Path(self._items[idx]["path"])
        if not path.exists():
            self.view.setPlainText("(file not found)")
            return
        try:
            txt = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            self.view.setPlainText(f"Could not read file:\n{e}")
            return
        self.view.setPlainText(self._pretty_json(txt) if path.suffix.lower() == ".json" else txt)

    def open_dir(self):
        base = self._base_dir
        try:
            if base.exists():
                os.startfile(str(base))
            else:
                self.view.setPlainText(f"Folder does not exist:\n{base}")
        except Exception as e:
            self.view.setPlainText(f"Could not open folder:\n{e}")