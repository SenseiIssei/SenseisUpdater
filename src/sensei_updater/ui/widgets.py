from PySide6.QtCore import Qt, QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QProgressBar,
    QListWidget, QListWidgetItem, QStyle, QLabel, QPushButton, QFrame, QStackedWidget, QGraphicsOpacityEffect
)

def std_icon(name: QStyle.StandardPixmap):
    return QApplication.style().standardIcon(name)

def safe_set_text(lbl: QLabel, text: str):
    if lbl and lbl.parent():
        lbl.setText(text or "")

class GlassCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("Card")
        self.setFrameShape(QFrame.NoFrame)
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(18, 18, 18, 18)
        self.v.setSpacing(12)

class Header(QWidget):
    def __init__(self, text):
        super().__init__()
        self.setObjectName("Header")
        h = QHBoxLayout(self)
        h.setContentsMargins(16, 12, 16, 12)
        t = QLabel(text)
        t.setStyleSheet("color:#e6eeff;font-size:18px;font-weight:600")
        h.addWidget(t, 1)

class Sidebar(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(12, 12, 12, 12)
        self.v.setSpacing(8)
        self.v.addStretch(1)
        self.buttons = []
    def add(self, text, cb, selected=False):
        b = QPushButton(text)
        b.setObjectName("NavButton")
        b.setIcon(std_icon(QStyle.SP_ArrowRight))
        b.setProperty("selected", "true" if selected else "false")
        b.clicked.connect(cb)
        self.v.insertWidget(self.v.count() - 1, b)
        self.buttons.append(b)
        return b
    def select(self, btn):
        for b in self.buttons:
            b.setProperty("selected", "false")
            b.style().unpolish(b); b.style().polish(b)
        btn.setProperty("selected", "true")
        btn.style().unpolish(btn); btn.style().polish(btn)

class MetricTile(GlassCard):
    def __init__(self, label, value):
        super().__init__()
        val = QLabel(value); val.setObjectName("MetricValue")
        lab = QLabel(label.upper()); lab.setObjectName("MetricLabel")
        self.v.addWidget(val); self.v.addWidget(lab)

class ResponsiveGrid(QWidget):
    def __init__(self, hpad=24, vpad=24, min_col_w=240, max_cols=4):
        super().__init__()
        self.hpad, self.vpad, self.min_col_w, self.max_cols = hpad, vpad, min_col_w, max_cols
        self.g = QGridLayout(self)
        self.g.setContentsMargins(hpad, vpad, hpad, vpad)
        self.g.setHorizontalSpacing(16); self.g.setVerticalSpacing(16)
        self.tiles = []; self.row_stretch_added = False
    def add(self, w):
        self.tiles.append(w); self._relayout()
    def resizeEvent(self, e):
        self._relayout(); super().resizeEvent(e)
    def _relayout(self):
        if not self.tiles: return
        ww = max(1, self.width() - self.hpad * 2)
        cols = max(1, min(self.max_cols, ww // self.min_col_w))
        while self.g.count():
            it = self.g.takeAt(0); w = it.widget()
            if w: w.setParent(None)
        r = c = 0
        for w in self.tiles:
            self.g.addWidget(w, r, c)
            c += 1
            if c >= cols: c = 0; r += 1
        if not self.row_stretch_added:
            self.g.setRowStretch(r + 1, 1); self.row_stretch_added = True

class StepListItem(QWidget):
    def __init__(self, title):
        super().__init__()
        h = QHBoxLayout(self); h.setContentsMargins(10, 8, 10, 8)
        self.dot = QLabel("●"); self.dot.setStyleSheet("color:#8fa1c5;font-size:14px;font-weight:700")
        self.title = QLabel(title); self.title.setStyleSheet("color:#eef3ff")
        self.badge = QLabel(""); self.badge.setObjectName("Chip"); self.badge.setVisible(False)
        h.addWidget(self.dot); h.addSpacing(8); h.addWidget(self.title, 1); h.addWidget(self.badge)
    def set_running(self):
        self.dot.setText("●"); self.dot.setStyleSheet("color:#66a1ff;font-size:14px;font-weight:700"); self.badge.setVisible(False)
    def set_done(self, text=None):
        self.dot.setText("✔"); self.dot.setStyleSheet("color:#5fd28f;font-size:14px;font-weight:900")
        if text: self.badge.setText(text); self.badge.setVisible(True)
    def set_fail(self, text=None):
        self.dot.setText("✘"); self.dot.setStyleSheet("color:#ff6b6b;font-size:14px;font-weight:900")
        if text: self.badge.setText(text); self.badge.setVisible(True)

class SelectCard(GlassCard):
    """Reusable selector with better visuals and clear selection count."""
    def __init__(self, title):
        super().__init__()
        self.title = QLabel(title); self.title.setStyleSheet("color:#e6eeff;font-weight:700")
        self.btn_scan = QPushButton("Scan"); self.btn_scan.setIcon(std_icon(QStyle.SP_BrowserReload))
        self.btn_sel_all = QPushButton("Select All"); self.btn_sel_all.setIcon(std_icon(QStyle.SP_DialogYesButton))
        self.btn_sel_none = QPushButton("Select None"); self.btn_sel_none.setIcon(std_icon(QStyle.SP_DialogNoButton))
        for b in (self.btn_scan, self.btn_sel_all, self.btn_sel_none):
            b.setObjectName("PrimaryButton")

        head = QHBoxLayout()
        head.addWidget(self.title, 1); head.addWidget(self.btn_scan); head.addWidget(self.btn_sel_all); head.addWidget(self.btn_sel_none)
        self.v.addLayout(head)

        self.msg = QLabel(""); self.msg.setObjectName("Chip")
        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.ExtendedSelection)
        # Visual clarity for checked vs unchecked (QSS targets ::indicator, see styles.qss)
        self.list.setAlternatingRowColors(True)

        self.v.addWidget(self.msg)
        self.v.addWidget(self.list, 1)

        self.pb = QProgressBar(); self.pb.setRange(0, 100); self.pb.hide()
        self.v.addWidget(self.pb)

        self.btn_sel_all.clicked.connect(self.select_all)
        self.btn_sel_none.clicked.connect(self.select_none)
        self.list.itemChanged.connect(self._set_checked_count)

    def clear(self):
        self.list.clear(); self.msg.clear(); self._set_checked_count()

    def add_row(self, text: str, checked: bool = True):
        it = QListWidgetItem(text)
        it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
        it.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        # bold selected rows via data role (QSS can style [selected="true"])
        it.setData(Qt.UserRole, text)
        self.list.addItem(it)
        return it

    def selected_ids(self) -> list[str]:
        ids = []
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.flags() & Qt.ItemIsUserCheckable and it.checkState() == Qt.Checked:
                ids.append((it.text() or "").split("  ")[0])
        return [x for x in ids if x]

    def select_all(self):
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.flags() & Qt.ItemIsUserCheckable:
                it.setCheckState(Qt.Checked)
        self._set_checked_count()

    def select_none(self):
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.flags() & Qt.ItemIsUserCheckable:
                it.setCheckState(Qt.Unchecked)
        self._set_checked_count()

    def _set_checked_count(self):
        total = checked = 0
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.flags() & Qt.ItemIsUserCheckable:
                total += 1
                if it.checkState() == Qt.Checked:
                    checked += 1
        self.msg.setText(f"Selected {checked} of {total}" if total else "")

class PageStack(QStackedWidget):
    def __init__(self):
        super().__init__(); self._anim = None
    def setCurrentIndexAnimated(self, idx):
        old = self.currentWidget(); super().setCurrentIndex(idx); new = self.currentWidget()
        if not old or not new or old is new: return
        eff = QGraphicsOpacityEffect(new); new.setGraphicsEffect(eff); eff.setOpacity(0.0)
        a = QPropertyAnimation(eff, b"opacity", self)
        a.setDuration(160); a.setStartValue(0.0); a.setEndValue(1.0); a.setEasingCurve(QEasingCurve.OutCubic)
        self._anim = a; a.start()