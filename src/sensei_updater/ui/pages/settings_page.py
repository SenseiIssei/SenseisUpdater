from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox, QTimeEdit, QSpinBox, QListWidget, QListWidgetItem
from ..widgets import GlassCard, Header

class SettingsPage(QWidget):
    def __init__(self, cfg, scheduler, app_service):
        super().__init__()
        self.cfg = cfg
        self.scheduler = scheduler
        self.app = app_service

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(Header("Settings"))

        card_defaults = GlassCard()
        ld = QVBoxLayout()
        ld.setContentsMargins(0, 0, 0, 0)

        row1 = QHBoxLayout()
        self.chk_yes = QCheckBox("Assume --yes for app updates")
        self.chk_skip_store = QCheckBox("Skip Microsoft Store during scan")
        self.chk_force_refresh = QCheckBox("Force refresh cache on scan")
        row1.addWidget(self.chk_yes)
        row1.addWidget(self.chk_skip_store)
        row1.addWidget(self.chk_force_refresh)
        row1.addStretch(1)
        ld.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Scan timeout (sec)"))
        self.spn_timeout = QSpinBox()
        self.spn_timeout.setRange(10, 600)
        self.spn_timeout.setSingleStep(5)
        row2.addWidget(self.spn_timeout)
        row2.addSpacing(16)
        row2.addWidget(QLabel("Cache TTL (minutes)"))
        self.spn_cache = QSpinBox()
        self.spn_cache.setRange(1, 480)
        row2.addWidget(self.spn_cache)
        row2.addStretch(1)
        ld.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Default profile"))
        self.cmb_profile = QComboBox()
        self.btn_profile_save = QPushButton("Save Profile From Selection")
        row3.addWidget(self.cmb_profile, 1)
        row3.addWidget(self.btn_profile_save)
        ld.addLayout(row3)

        card_defaults.v.addLayout(ld)

        card_profiles = GlassCard()
        lp = QVBoxLayout()
        lp.setContentsMargins(0, 0, 0, 0)

        rowP1 = QHBoxLayout()
        rowP1.addWidget(QLabel("Profiles"))
        self.txt_profile_name = QLineEdit()
        self.txt_profile_name.setPlaceholderText("profile name")
        self.btn_create_profile = QPushButton("Create/Update")
        self.btn_delete_profile = QPushButton("Delete")
        rowP1.addWidget(self.txt_profile_name, 1)
        rowP1.addWidget(self.btn_create_profile)
        rowP1.addWidget(self.btn_delete_profile)
        lp.addLayout(rowP1)

        self.list_profile_ids = QListWidget()
        self.list_profile_ids.setSelectionMode(QListWidget.ExtendedSelection)
        lp.addWidget(self.list_profile_ids)

        rowP2 = QHBoxLayout()
        self.btn_export = QPushButton("Export Profiles")
        self.btn_import = QPushButton("Import Profiles")
        rowP2.addWidget(self.btn_export)
        rowP2.addWidget(self.btn_import)
        rowP2.addStretch(1)
        lp.addLayout(rowP2)

        card_profiles.v.addLayout(lp)

        outer = QVBoxLayout()
        outer.setContentsMargins(24, 24, 24, 24)
        outer.addWidget(card_defaults)
        outer.addWidget(card_profiles)
        v.addLayout(outer)

        self._load_defaults()
        self._load_profiles()

        self.btn_profile_save.clicked.connect(self._save_defaults)
        self.chk_yes.toggled.connect(self._save_defaults)
        self.chk_skip_store.toggled.connect(self._save_defaults)
        self.chk_force_refresh.toggled.connect(self._save_defaults)
        self.spn_timeout.valueChanged.connect(self._save_defaults)
        self.spn_cache.valueChanged.connect(self._save_defaults)
        self.cmb_profile.currentTextChanged.connect(self._save_defaults)
        self.btn_create_profile.clicked.connect(self._create_or_update_profile)
        self.btn_delete_profile.clicked.connect(self._delete_profile)
        self.btn_export.clicked.connect(self._export_profiles)
        self.btn_import.clicked.connect(self._import_profiles)

    def _load_defaults(self):
        d = self.cfg.get_defaults()
        self.chk_yes.setChecked(bool(d.get("yes")))
        self.chk_skip_store.setChecked(bool(d.get("skip_store_scan", True)))
        self.chk_force_refresh.setChecked(bool(d.get("force_refresh")))
        self.spn_timeout.setValue(int(d.get("scan_timeout_sec", 45)))
        self.spn_cache.setValue(int(d.get("cache_ttl_minutes", 60)))
        self.cmb_profile.clear()
        names = [""] + self.cfg.list_profiles()
        self.cmb_profile.addItems(names)
        if d.get("profile") and d.get("profile") in names:
            self.cmb_profile.setCurrentText(d.get("profile"))

    def _load_profiles(self):
        self.list_profile_ids.clear()
        d = self.cfg.get_defaults()
        prof = d.get("profile")
        ids = self.cfg.get_profile(prof) if prof else set()
        for pid in sorted(ids):
            it = QListWidgetItem(pid)
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.list_profile_ids.addItem(it)

    def _save_defaults(self):
        kv = {
            "yes": self.chk_yes.isChecked(),
            "skip_store_scan": self.chk_skip_store.isChecked(),
            "force_refresh": self.chk_force_refresh.isChecked(),
            "scan_timeout_sec": int(self.spn_timeout.value()),
            "cache_ttl_minutes": int(self.spn_cache.value()),
            "profile": self.cmb_profile.currentText() or None
        }
        self.cfg.set_defaults(kv)
        self._load_profiles()

    def _create_or_update_profile(self):
        name = (self.txt_profile_name.text() or "").strip()
        if not name:
            return
        d = self.cfg.get_defaults()
        prof = d.get("profile")
        ids = sorted(set(self.cfg.get_profile(prof))) if prof else []
        self.cfg.set_profile(name, ids)
        self._load_defaults()
        self.cmb_profile.setCurrentText(name)
        self._load_profiles()

    def _delete_profile(self):
        name = (self.txt_profile_name.text() or "").strip()
        if not name:
            return
        cur = dict(self.cfg.data.get("profiles", {}))
        if name in cur:
            del cur[name]
            self.cfg.data["profiles"] = cur
            self.cfg.save()
            self._load_defaults()
            self._load_profiles()

    def _export_profiles(self):
        path = self.cfg.export_profiles("%LOCALAPPDATA%\\SenseiUpdater\\profiles.json")
        _ = path

    def _import_profiles(self):
        ok, _ = self.cfg.import_profiles("%LOCALAPPDATA%\\SenseiUpdater\\profiles.json", merge=True)
        if ok:
            self._load_defaults()
            self._load_profiles()