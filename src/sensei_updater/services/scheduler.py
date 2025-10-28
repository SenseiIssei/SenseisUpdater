import os
from pathlib import Path
from ..core.process import Process
from ..core.console import Console
from ..core.admin import is_admin

class SchedulerService:
    def __init__(self, console: Console):
        self.console = console
        self.proc = Process(debug=console.debug, dry_run=console.dry_run)

    def resolve_executable_and_args(self, extra_args: list[str]):
        exe = os.environ.get("SENSEI_EXE_PATH")
        if not exe:
            exe = Path(os.path.realpath(getattr(__import__("sys"), "executable")))
        args = " ".join(extra_args or [])
        return str(exe), args

    def _create_common(self, sc: str, d_arg: list[str], st_time: str, task_name: str, exe: str, args: str):
        """
        Try user-level task first (no admin required).
        If still access denied and we’re admin, retry with /RL HIGHEST.
        """
        base = ["schtasks","/Create","/SC",sc] + d_arg + [
            "/TN", task_name,
            "/TR", f'"{exe}" {args}',
            "/ST", st_time,
            "/RL", "LIMITED",  # <= user-friendly default
            "/F"
        ]
        rc = self.proc.run_stream(base)
        if rc == 0:
            return True

        # If access denied but we are elevated, try highest
        if is_admin():
            rc = self.proc.run_stream(["schtasks","/Create","/SC",sc] + d_arg + [
                "/TN", task_name,
                "/TR", f'"{exe}" {args}',
                "/ST", st_time,
                "/RL", "HIGHEST",
                "/F"
            ])
            return rc == 0

        return False  # still denied

    def create(self, schedule: str, st_time: str, task_name: str, extra_args: list[str]):
        exe, args = self.resolve_executable_and_args(extra_args)
        if schedule == "weekly":
            return self._create_common("WEEKLY", ["/D","MON"], st_time, task_name, exe, args)
        if schedule == "monthly":
            return self._create_common("MONTHLY", ["/D","1"], st_time, task_name, exe, args)
        return False

    def delete(self, task_name: str):
        rc = self.proc.run_stream(["schtasks","/Delete","/TN",task_name,"/F"])
        return rc == 0

    def exists(self, task_name: str):
        rc,_ = self.proc.run_capture(["schtasks","/Query","/TN",task_name])
        return rc == 0