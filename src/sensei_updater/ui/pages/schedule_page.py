from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QTimeEdit, QLineEdit, QCheckBox
)

from ..widgets import Header, GlassCard, safe_set_text


class SchedulePage(QWidget):
    def __init__(self, cfg, sched):
        super().__init__()
        self.cfg = cfg
        self.sched = sched

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 16)
        root.setSpacing(8)

        root.addWidget(Header("Schedule"))

        card = GlassCard()
        card.v.setContentsMargins(20, 16, 20, 16)
        card.v.setSpacing(12)

        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)

        self.chk_enable = QCheckBox("Enable scheduled auto update")
        grid.addWidget(self.chk_enable, 0, 0, 1, 2)

        grid.addWidget(QLabel("Frequency"), 1, 0)
        self.cmb_freq = QComboBox()
        self.cmb_freq.addItems(["weekly", "monthly"])
        grid.addWidget(self.cmb_freq, 1, 1)

        grid.addWidget(QLabel("Time"), 1, 2)
        self.time = QTimeEdit()
        self.time.setDisplayFormat("HH:mm")
        grid.addWidget(self.time, 1, 3)

        grid.addWidget(QLabel("Task name"), 2, 0)
        self.task_name = QLineEdit()
        grid.addWidget(self.task_name, 2, 1, 1, 3)

        btns = QHBoxLayout()
        btns.setContentsMargins(0, 0, 0, 0)
        btns.setSpacing(10)
        self.btn_apply = QPushButton("Apply")
        self.btn_apply.setObjectName("PrimaryButton")
        self.btn_remove = QPushButton("Remove")
        self.btn_refresh = QPushButton("Refresh")
        btns.addWidget(self.btn_apply)
        btns.addWidget(self.btn_remove)
        btns.addWidget(self.btn_refresh)
        btns.addStretch(1)
        grid.addLayout(btns, 3, 0, 1, 4)

        side = GlassCard()
        side.v.setContentsMargins(12, 12, 12, 12)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        side.v.addWidget(self.status)
        side.setMinimumWidth(240)
        side.setMaximumWidth(280)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)
        row.addWidget(body, 1)
        row.addWidget(side)

        card.v.addLayout(row)
        root.addWidget(card)

        self.btn_apply.clicked.connect(self.apply)
        self.btn_remove.clicked.connect(self.remove)
        self.btn_refresh.clicked.connect(self.refresh)

        self.refresh()

    def _fmt_time(self) -> str:
        return self.time.time().toString("HH:mm")

    def refresh(self):
        s = self.cfg.get_schedule() or {}
        self.chk_enable.setChecked(bool(s.get("enabled")))
        freq = s.get("frequency") or "weekly"
        idx = max(0, self.cmb_freq.findText(freq))
        self.cmb_freq.setCurrentIndex(idx)
        try:
            hh, mm = str(s.get("time") or "09:00").split(":")
            self.time.setTime(QTime(int(hh), int(mm)))
        except Exception:
            self.time.setTime(QTime(9, 0))
        self.task_name.setText(s.get("task_name") or "SenseisUpdater Auto Update")
        exists = False
        try:
            exists = self.sched.exists(self.task_name.text().strip())
        except Exception:
            exists = False
        state = "Enabled" if s.get("enabled") and exists else "Disabled"
        safe_set_text(self.status, f"Task exists • {state}")

    def apply(self):
        enabled = self.chk_enable.isChecked()
        freq = self.cmb_freq.currentText().strip()
        tname = self.task_name.text().strip() or "SenseisUpdater Auto Update"
        ok = True
        if enabled and freq:
            args = list((self.cfg.get_schedule() or {}).get("args") or [])
            ok = self.sched.create(freq, self._fmt_time(), tname, args)
        if ok:
            self.cfg.set_schedule(enabled, freq if enabled else None, self._fmt_time(), tname, (self.cfg.get_schedule() or {}).get("args") or [])
            safe_set_text(self.status, "Schedule applied")
        else:
            safe_set_text(self.status, "Failed to apply schedule")
        self.refresh()

    def remove(self):
        tname = self.task_name.text().strip()
        if not tname:
            safe_set_text(self.status, "No task name")
            return
        ok = self.sched.delete(tname)
        if ok:
            self.cfg.set_schedule(False, None, self._fmt_time(), tname, (self.cfg.get_schedule() or {}).get("args") or [])
            safe_set_text(self.status, "Schedule removed")
        else:
            safe_set_text(self.status, "Could not remove schedule")
        self.refresh()