import argparse
from pathlib import Path
from .core.console import Console
from .domain.config import ConfigStore
from .domain.reports import RunReport
from .services.drivers import DriverService
from .services.apps import AppService
from .services.system import SystemService
from .ui.menu import Menu

def main():
    parser = argparse.ArgumentParser(description="Sensei's Updater")
    parser.add_argument("--quick", action="store_true", help="Quick maintenance batch (admin recommended)")
    parser.add_argument("--drivers", action="store_true", help="Driver updates only (admin)")
    parser.add_argument("--apps", action="store_true", help="App updates selector (user recommended)")
    parser.add_argument("--cleanup", action="store_true", help="Clean TEMP & empty Recycle Bin (admin)")
    parser.add_argument("--health", action="store_true", help="DISM + SFC (admin)")
    parser.add_argument("--startup", action="store_true", help="Show startup programs")

    parser.add_argument("--profile", type=str, default=None, help="Load a saved profile of app IDs, e.g. --profile gaming")
    parser.add_argument("--yes", action="store_true", help="Apply without interactive confirmation")
    parser.add_argument("--report", choices=["json", "txt"], help="Write a run report in given format")
    parser.add_argument("--out", type=str, help="Output path for --report")

    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    parser.add_argument("--debug", action="store_true", help="Print executed commands")
    args = parser.parse_args()

    console = Console(debug=args.debug, dry_run=args.dry_run)
    console.enable_windows_ansi_utf8()
    console.banner()
    console.pixel_art()

    cfg = ConfigStore()
    app = AppService(console=console, cfg=cfg)
    drivers = DriverService(console=console)
    system = SystemService(console=console)

    try:
        if system.has_pending_reboot():
            console.warn("Windows indicates a pending reboot. Consider rebooting before updates to avoid conflicts.")
    except Exception:
        pass

    if args.quick or args.drivers or args.apps or args.cleanup or args.health or args.startup or args.profile:
        report = RunReport()

        selected_ids = []
        if args.profile:
            selected_ids = list(cfg.get_profile(args.profile))
            if not selected_ids:
                console.warn(f"Profile '{args.profile}' is empty or missing.")

        if args.quick or args.drivers:
            ok, reboot = drivers.update_drivers()
            report.driver_success = ok
            report.reboot_required = report.reboot_required or reboot

        if args.quick or args.apps or args.profile:
            if selected_ids:
                res = app.update_ids(selected_ids)
            else:
                upgrades = app.list_upgrades()
                if upgrades and args.yes:
                    res = app.update_ids([p["Id"] for p in upgrades])
                elif upgrades and not args.yes:
                    console.info("Opening interactive selector (no --yes provided).")
                    from .ui.selector import Selector
                    chosen = Selector(console, cfg).loop(upgrades, app, title="Upgradable Apps (winget)")
                    if chosen:
                        res = app.update_ids(chosen)
                    else:
                        res = {"updated": [], "interactive": [], "reinstalled": [],
                               "skipped": [], "store_skipped": [], "failed": []}
                else:
                    console.warn("No upgrades detected by winget.")
                    res = {"updated": [], "interactive": [], "reinstalled": [],
                           "skipped": [], "store_skipped": [], "failed": []}

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
        from .ui.menu import Menu as _Menu
        _Menu(console, app, drivers, system, cfg)._print_summary(report)

        if args.report and args.out:
            out_path = Path(args.out).expanduser()
            try:
                report.save(args.report, out_path)
                console.ok(f"Report written: {out_path}")
            except Exception as e:
                console.warn(f"Could not write report: {e}")
        return

    menu = Menu(console=console, app=app, drivers=drivers, system=system, cfg=cfg)
    menu.run()