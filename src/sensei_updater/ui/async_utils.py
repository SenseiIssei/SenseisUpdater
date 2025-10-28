from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot, QEasingCurve, QPropertyAnimation, QRect
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar


class Worker(QObject):
    progress = Signal(int)
    message = Signal(str)
    result = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self):
        try:
            r = self.fn(self._emit_progress, self._emit_message, *self.args, **self.kwargs)
            self.result.emit(r)
        except Exception as e:
            self.failed.emit(str(e))
        finally:
            self.finished.emit()

    def _emit_progress(self, v: int):
        self.progress.emit(int(max(0, min(100, v))))

    def _emit_message(self, s: str):
        self.message.emit(s or "")


def run_async(fn, *args, **kwargs):
    t = QThread()
    w = Worker(fn, *args, **kwargs)
    w.moveToThread(t)
    t.started.connect(w.run, Qt.QueuedConnection)
    return t, w


class BusyOverlay(QWidget):
    def __init__(self, parent: QWidget, compact: bool = False):
        super().__init__(parent)
        self.setObjectName("Overlay")
        self.compact = bool(compact)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, not self.compact)
        self.setStyleSheet("background:rgba(10,10,10,140);" if not self.compact else "background:transparent;")
        if self.compact:
            self.label = QLabel("", self)
            self.label.setStyleSheet("color:#FFD166;font-size:12px;")
            self.bar = QProgressBar(self)
            self.bar.setFixedHeight(8)
            self.bar.setRange(0, 0)
            self.bar.setTextVisible(False)
        else:
            lay = QVBoxLayout(self)
            lay.setContentsMargins(48, 48, 48, 48)
            lay.setAlignment(Qt.AlignCenter)
            self.label = QLabel("Working…")
            self.label.setStyleSheet("color:#FFD166;font-size:16px;")
            self.bar = QProgressBar()
            self.bar.setRange(0, 100)
            self.bar.setValue(0)
            lay.addWidget(self.label)
            lay.addWidget(self.bar)
        self.hide()
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setEasingCurve(QEasingCurve.InOutQuad)
        self._fade.setDuration(160)
        self._fade.finished.connect(self._finish_hide, Qt.QueuedConnection)
        self._hiding = False

    def _finish_hide(self):
        if self._hiding:
            self.hide()
            self._hiding = False

    def resizeEvent(self, e):
        if self.compact:
            w = max(260, self.parent().width() // 4)
            r = QRect(self.parent().width() - w - 16, 12, w, 28)
            self.setGeometry(r)
            self.label.setGeometry(0, 0, w, 12)
            self.bar.setGeometry(0, 16, w, 8)
        else:
            self.setGeometry(self.parent().rect())

    def show_smooth(self):
        if self.compact:
            self.setWindowOpacity(1.0)
            self.show()
            self.raise_()
            return
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self._fade.stop()
        self._hiding = False
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()

    def hide_smooth(self):
        if self.compact:
            self.hide()
            return
        self._fade.stop()
        self._hiding = True
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.start()


class ProgressDriver(QObject):
    set_target = Signal(int)
    start = Signal()
    finish = Signal()

    def __init__(self, bar: QProgressBar):
        super().__init__(bar)
        self.bar = bar
        self._cur = 0
        self._target = 0
        self._tick = QTimer(self)
        self._tick.setInterval(40)
        self._tick.timeout.connect(self._on_tick, Qt.QueuedConnection)
        self.start.connect(self._on_start, Qt.QueuedConnection)
        self.finish.connect(self._on_finish, Qt.QueuedConnection)
        self.set_target.connect(self._on_set_target, Qt.QueuedConnection)

    def _on_start(self):
        if self.bar.maximum() == 0:
            return
        self._cur = 0
        self._target = 0
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self._tick.start()

    def _on_set_target(self, v: int):
        if self.bar.maximum() == 0:
            return
        self._target = max(0, min(100, v))

    def _on_finish(self):
        if self.bar.maximum() == 0:
            return
        self._target = 100
        self._tick.stop()
        self.bar.setValue(100)

    def _on_tick(self):
        if self.bar.maximum() == 0:
            return
        if self._cur < self._target:
            self._cur += max(1, int((self._target - self._cur) * 0.18))
            self.bar.setValue(self._cur)


class JobController(QObject):
    def __init__(self, owner: QWidget, overlay: BusyOverlay):
        super().__init__(owner)
        self.owner = owner
        self.overlay = overlay
        self._prog = ProgressDriver(self.overlay.bar)
        self._active = set()

    def start(self, thread: QThread, worker: Worker, label: str, disable_widgets, on_done, timeout_ms: int = 60000):
        def setup_ui():
            self.overlay.label.setText(label or "Working…")
            if not self.overlay.compact:
                self.overlay.bar.setRange(0, 100)
                self.overlay.bar.setValue(0)
            else:
                self.overlay.bar.setRange(0, 0)
            self.overlay.show_smooth()
            self._prog.start.emit()
            for w in (disable_widgets or []):
                try:
                    w.setEnabled(False)
                except Exception:
                    pass

        def finish_ui():
            self._prog.finish.emit()
            self.overlay.hide_smooth()
            for w in (disable_widgets or []):
                try:
                    w.setEnabled(True)
                except Exception:
                    pass

        timer = QTimer(self)
        timer.setSingleShot(True)

        def cleanup():
            try:
                if thread.isRunning():
                    thread.quit()
                QTimer.singleShot(0, lambda: thread.wait(1500))
            except Exception:
                pass
            self._active.discard((thread, worker, timer))

        def on_timeout():
            finish_ui()
            cleanup()
            try:
                on_done({"error": "timeout"})
            except Exception:
                pass

        def on_ok(res):
            finish_ui()
            cleanup()
            try:
                on_done(res)
            except Exception:
                pass

        def on_fail(msg):
            finish_ui()
            cleanup()
            try:
                on_done({"error": msg})
            except Exception:
                pass

        setup_ui()
        self._active.add((thread, worker, timer))
        worker.progress.connect(self._prog.set_target, Qt.QueuedConnection)
        worker.message.connect(lambda s: self.overlay.label.setText(s or label), Qt.QueuedConnection)
        worker.result.connect(on_ok, Qt.QueuedConnection)
        worker.failed.connect(on_fail, Qt.QueuedConnection)
        worker.finished.connect(thread.quit, Qt.QueuedConnection)
        thread.finished.connect(worker.deleteLater, Qt.QueuedConnection)
        thread.finished.connect(thread.deleteLater, Qt.QueuedConnection)
        self.owner.destroyed.connect(lambda: QTimer.singleShot(0, cleanup), Qt.QueuedConnection)
        thread.finished.connect(lambda: QTimer.singleShot(0, cleanup), Qt.QueuedConnection)
        timer.timeout.connect(on_timeout, Qt.QueuedConnection)
        timer.start(max(3000, int(timeout_ms) if timeout_ms else 60000))
        thread.start()