# sensei_updater/main.py
import argparse
import sys
from pathlib import Path
from .core.console import Console
from .domain.config import ConfigStore
from .domain.reports import RunReport
from .services.drivers_service import DriverService
from .services.apps_service import AppService
from .services.system import SystemService
from .services.scheduler import SchedulerService
from .services.diagnostics import DiagnosticsService

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Sensei's Updater")
    p.add_argument("--gui", action="store_true")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p

def run_gui(argv=None) -> int:
    from .ui.main_window import start_gui
    args = _build_parser().parse_args(argv)
    console = Console(debug=args.debug, dry_run=args.dry_run)
    console.enable_windows_ansi_utf8()
    cfg = ConfigStore()
    app = AppService(console=console, cfg=cfg)
    drivers = DriverService(console=console)
    system = SystemService(console=console)
    sched = SchedulerService(console=console)
    try:
        system.ensure_app_installer()
    except Exception:
        pass
    try:
        from . import __version__ as VERSION_TEXT
    except Exception:
        VERSION_TEXT = "v2.0"
    qss_path = str(Path(__file__).with_name("ui").joinpath("styles.qss"))
    class ReportsExport:
        def export_json(self, path, data):
            r = RunReport()
            r.save("json", Path(path))
    return start_gui(console, app, drivers, system, cfg, sched, ReportsExport(), VERSION_TEXT, qss_path)

def run_cli(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    console = Console(debug=args.debug, dry_run=args.dry_run)
    console.enable_windows_ansi_utf8()
    console.banner()
    if args.gui:
        return run_gui(argv)
    console.info("No action flags provided. Use --gui to start the graphical app.")
    return 0

def run() -> int:
    args = sys.argv[1:]
    wants_gui = ("--gui" in args) or getattr(sys, "frozen", False)
    if wants_gui:
        args = [a for a in args if a != "--gui"]
        return run_gui(args)
    return run_cli(args)

def main() -> int:
    return run()

if __name__ == "__main__":
    sys.exit(main())