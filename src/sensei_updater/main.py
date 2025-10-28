import argparse, os, sys
from pathlib import Path
from .core.console import Console
from .domain.config import ConfigStore
from .domain.reports import RunReport
from .services.drivers import DriverService
from .services.apps import AppService
from .services.system import SystemService
from .services.diagnostics import DiagnosticsService
from .services.scheduler import SchedulerService

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Sensei's Updater")
    p.add_argument("--quick", action="store_true")
    p.add_argument("--drivers", action="store_true")
    p.add_argument("--apps", action="store_true")
    p.add_argument("--cleanup", action="store_true")
    p.add_argument("--health", action="store_true")
    p.add_argument("--startup", action="store_true")
    p.add_argument("--profile", type=str, default=None)
    p.add_argument("--yes", action="store_true")
    p.add_argument("--report", choices=["json","txt"])
    p.add_argument("--out", type=str)
    p.add_argument("--diagnostics", action="store_true")
    p.add_argument("--diag-out", type=str)
    p.add_argument("--schedule", choices=["weekly","monthly"])
    p.add_argument("--time", type=str, default="09:00")
    p.add_argument("--task-name", type=str, default="SenseisUpdater Auto Update")
    p.add_argument("--unschedule", action="store_true")
    p.add_argument("--export", type=str)
    p.add_argument("--import", dest="import_path", type=str)
    p.add_argument("--force-refresh", action="store_true")
    p.add_argument("--skip-store-scan", action="store_true")
    p.add_argument("--scan-timeout", type=int)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--gui", action="store_true")
    p.add_argument("--qss", type=str)
    return p

def _print_summary(console: Console, report: RunReport):
    console.info("— Summary —")
    if report.updated:
        console.ok(f"Updated: {', '.join(report.updated)}")
    if report.interactive:
        console.ok(f"Interactive: {', '.join(report.interactive)}")
    if report.reinstalled:
        console.ok(f"Reinstalled: {', '.join(report.reinstalled)}")
    if report.skipped:
        console.warn(f"Skipped: {', '.join(report.skipped)}")
    if report.store_skipped:
        console.warn(f"Store-skipped: {', '.join(report.store_skipped)}")
    if report.failed:
        console.err(f"Failed: {', '.join(report.failed)}")
    console.info(f"Reboot required: {'Yes' if report.reboot_required else 'No'}")

def run_gui(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    console = Console(debug=False, dry_run=False)
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

    qss_path = None
    if argv:
        for i, a in enumerate(list(argv)):
            if a == "--qss" and i + 1 < len(argv):
                qss_path = argv[i + 1]
                break
    if not qss_path:
        qss_path = str(Path(__file__).with_name("ui").joinpath("styles.qss"))

    class ReportsExport:
        def export_json(self, path, data):
            r = RunReport()
            r.save("json", Path(path))

    from .ui.main_window import start_gui
    start_gui(console, app, drivers, system, cfg, sched, ReportsExport(), VERSION_TEXT, qss_path)
    return 0

def run_cli(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    console = Console(debug=args.debug, dry_run=args.dry_run)
    console.enable_windows_ansi_utf8()
    console.banner()
    console.pixel_art()

    cfg = ConfigStore()
    defaults = cfg.get_defaults()

    if args.profile is None and defaults.get("profile"):
        args.profile = defaults.get("profile")
    if not args.yes and defaults.get("yes"):
        args.yes = True
    if not args.report:
        args.report = defaults.get("report") or "json"
    if not args.out:
        args.out = defaults.get("out")
    if not args.scan_timeout:
        args.scan_timeout = int(defaults.get("scan_timeout_sec", 90))
    if not args.force_refresh and defaults.get("force_refresh"):
        args.force_refresh = True
    if not args.skip_store_scan and defaults.get("skip_store_scan"):
        args.skip_store_scan = True

    app = AppService(console=console, cfg=cfg)
    drivers = DriverService(console=console)
    system = SystemService(console=console)
    diag = DiagnosticsService(console=console, cfg=cfg, app=app, system=system)
    sched = SchedulerService(console=console)
    system.ensure_app_installer()

    try:
        if system.has_pending_reboot():
            console.warn("Windows indicates a pending reboot. Consider rebooting before updates to avoid conflicts.")
    except Exception:
        pass

    s = cfg.get_schedule()
    if s.get("enabled") and s.get("frequency") and s.get("task_name"):
        if not sched.exists(s["task_name"]):
            ok = sched.create(s["frequency"], s["time"], s["task_name"], s["args"])
            if ok:
                console.ok("Applied saved schedule.")
            else:
                console.warn("Failed to apply saved schedule.")

    if args.unschedule and args.task_name:
        if sched.delete(args.task_name):
            console.ok(f"Removed scheduled task: {args.task_name}")
        else:
            console.warn(f"Could not remove scheduled task: {args.task_name}")
        return 0

    if args.schedule:
        out_dir = Path(os.getenv("LOCALAPPDATA", str(Path.home()))).joinpath("SenseiUpdater")
        out_dir.mkdir(parents=True, exist_ok=True)
        extra = []
        if args.quick: extra += ["--quick"]
        if args.drivers: extra += ["--drivers"]
        if args.apps: extra += ["--apps"]
        if args.cleanup: extra += ["--cleanup"]
        if args.health: extra += ["--health"]
        if args.startup: extra += ["--startup"]
        if args.profile: extra += ["--profile", args.profile]
        if args.yes: extra += ["--yes"]
        extra += ["--report", args.report or "json", "--out", args.out or str(out_dir.joinpath("last-run.json"))]
        ok = sched.create(args.schedule, args.time, args.task_name, extra)
        if ok:
            cfg.set_schedule(True, args.schedule, args.time, args.task_name, extra)
            console.ok(f"Scheduled {args.schedule} at {args.time}: {args.task_name}")
        else:
            console.err("Scheduling failed.")
        return 0

    if args.export:
        out_path = cfg.export_profiles(args.export)
        console.ok(f"Exported profiles to {out_path}")
        return 0
    if args.import_path:
        ok, err = cfg.import_profiles(args.import_path, merge=True)
        if ok:
            console.ok("Imported profiles.")
        else:
            console.err(f"Import failed: {err}")
        return 0

    if args.gui:
        try:
            from . import __version__ as VERSION_TEXT
        except Exception:
            VERSION_TEXT = "v2.0"
        from .ui.main_window import start_gui
        qss = args.qss or str(Path(__file__).with_name("ui").joinpath("styles.qss"))
        class ReportsExport:
            def export_json(self, path, data):
                r = RunReport()
                r.save("json", Path(path))
        start_gui(console, app, drivers, system, cfg, sched, ReportsExport(), VERSION_TEXT, qss)
        return 0

    if args.quick or args.drivers or args.apps or args.cleanup or args.health or args.startup or args.profile or args.diagnostics:
        report = RunReport()
        selected_ids = list(cfg.get_profile(args.profile)) if args.profile else []

        if args.quick or args.drivers:
            ok, reboot = drivers.update_drivers()
            report.driver_success = ok
            report.reboot_required = report.reboot_required or reboot

        if args.quick or args.apps or args.profile:
            if selected_ids:
                res = app.update_ids(selected_ids)
            else:
                upgrades = app.list_upgrades(
                    force_refresh=args.force_refresh,
                    skip_store=args.skip_store_scan,
                    scan_timeout=args.scan_timeout
                )
                if upgrades and args.yes:
                    res = app.update_ids([p["Id"] for p in upgrades])
                elif upgrades and not args.yes:
                    console.warn("Upgrades found but no --yes provided; skipping installation. Use --yes or run with --gui.")
                    res = {"updated": [], "interactive": [], "reinstalled": [], "skipped": [], "store_skipped": [], "failed": []}
                else:
                    console.warn("No upgrades detected by winget.")
                    res = {"updated": [], "interactive": [], "reinstalled": [], "skipped": [], "store_skipped": [], "failed": []}

            report.updated.extend(res["updated"])
            report.interactive.extend(res["interactive"])
            report.reinstalled.extend(res["reinstalled"])
            report.skipped.extend(res["skipped"])
            report.store_skipped.extend(res["store_skipped"])
            report.failed.extend(res["failed"])

        if args.quick or args.cleanup:
            system.cleanup_temp()
            system.empty_recycle_bin()

        if args.quick or args.health:
            system.dism_sfc()

        if args.startup:
            system.show_startup()

        report.mark_finished()
        _print_summary(console, report)

        if args.report and args.out:
            out_path = Path(args.out).expanduser()
            try:
                report.save(args.report, out_path)
                console.ok(f"Report written: {out_path}")
            except Exception as e:
                console.warn(f"Could not write report: {e}")

        if args.diagnostics:
            zip_path = Path(args.diag_out).expanduser() if args.diag_out else Path.cwd() / "sensei-diagnostics.zip"
            try:
                DiagnosticsService(console=console, cfg=cfg, app=app, system=system).create(
                    zip_path=zip_path, report=report, report_fmt=args.report or "json"
                )
                console.ok(f"Diagnostics zip written: {zip_path}")
            except Exception as e:
                console.warn(f"Could not create diagnostics: {e}")
        return 0

    console.info("No action flags provided. Use --gui for the graphical app or see --help for CLI options.")
    _build_parser().print_help()
    return 0

def run() -> int:
    args = sys.argv[1:]
    wants_gui = ("--gui" in args) or getattr(sys, "frozen", False)
    if wants_gui:
        args = [a for a in args if a != "--gui"]
        return run_gui(args)
    return run_cli(args)

def main():
    return run_cli()

if __name__ == "__main__":
    sys.exit(main())