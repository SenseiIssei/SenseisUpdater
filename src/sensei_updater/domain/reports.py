import json, time
from pathlib import Path

class RunReport:
    def __init__(self):
        self.started = time.time()
        self.finished = None
        self.updated = []
        self.interactive = []
        self.reinstalled = []
        self.skipped = []
        self.store_skipped = []
        self.failed = []
        self.driver_success = False
        self.reboot_required = False
        self.notes = []

    def mark_finished(self):
        if not self.finished:
            self.finished = time.time()

    def to_dict(self):
        return {
            "started": self.started,
            "finished": self.finished,
            "updated": self.updated,
            "interactive": self.interactive,
            "reinstalled": self.reinstalled,
            "skipped": self.skipped,
            "store_skipped": self.store_skipped,
            "failed": self.failed,
            "driver_success": self.driver_success,
            "reboot_required": self.reboot_required,
            "notes": self.notes
        }

    def save(self, fmt: str, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "json":
            path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        else:
            lines = []
            lines.append("Sensei's Updater Report")
            lines.append("")
            lines.append(f"Driver success: {self.driver_success}")
            lines.append(f"Reboot required: {self.reboot_required}")
            def w(label, arr):
                if arr: lines.append(f"{label}: " + ", ".join(arr))
            w("Updated", self.updated)
            w("Updated (interactive)", self.interactive)
            w("Reinstalled", self.reinstalled)
            w("Skipped", self.skipped)
            w("Store skipped", self.store_skipped)
            w("Failed", self.failed)
            if self.notes: lines.append("Notes: " + "; ".join(self.notes))
            path.write_text("\n".join(lines), encoding="utf-8")