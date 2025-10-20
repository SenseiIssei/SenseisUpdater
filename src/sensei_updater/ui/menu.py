from ..core.colors import *
from .selector import Selector
from ..domain.reports import RunReport

class Menu:
    def __init__(self, console, app, drivers, system, cfg):
        self.console = console
        self.app = app
        self.drivers = drivers
        self.system = system
        self.cfg = cfg
        self.selector = Selector(console, cfg)

    def _print_summary(self, r: RunReport):
        r.mark_finished()
        self.console.header("Summary")
        print(f"Driver success: {r.driver_success}")
        print(f"Reboot required: {r.reboot_required}")
        def show(label, arr, color=WHITE):
            if arr:
                print(f"{color}{label}:{RESET} " + ", ".join(arr))
        show("Updated", r.updated, GREEN)
        show("Updated (interactive)", r.interactive, CYAN)
        show("Reinstalled", r.reinstalled, MAGENTA)
        show("Skipped", r.skipped, GRAY)
        show("Store skipped (admin)", r.store_skipped, YELLOW)
        show("Failed", r.failed, RED)
        if r.notes:
            print("Notes: " + "; ".join(r.notes))

    def run(self):
        while True:
            self.console.pixel_art()
            ctx = "Administrator" if self.console.is_admin() else "User"
            print(f"{GRAY}Context: {ctx}  •  Run app updates as User; run drivers/cleanup/health as Admin.{RESET}")
            self.console.header("Sensei's Updater — Menu")
            print(f"{ORANGE1}{BOLD}1){RESET} Create Restore Point  {GRAY}(Admin){RESET}")
            print(f"{ORANGE1}{BOLD}2){RESET} Update Drivers (Windows Update — Drivers)  {GRAY}(Admin){RESET}")
            print(f"{ORANGE1}{BOLD}3){RESET} Update Applications (choose dynamically)  {GRAY}(User recommended){RESET}")
            print(f"{ORANGE1}{BOLD}4){RESET} Cleanup TEMP + Empty Recycle Bin  {GRAY}(Admin){RESET}")
            print(f"{ORANGE1}{BOLD}5){RESET} Health Scan (DISM + SFC)  {GRAY}(Admin){RESET}")
            print(f"{ORANGE1}{BOLD}6){RESET} Show Startup Programs")
            print(f"{ORANGE1}{BOLD}7){RESET} QUICK: 1+2+3+4 in one go  {GRAY}(Admin){RESET}")
            print(f"{RED}{BOLD}0){RESET} Exit")
            print(f"{DIM}{GRAY}Support: https://ko-fi.com/senseiissei{RESET}")
            choice = input(f"{ORANGE2}{BOLD}Select → {RESET}").strip()

            if choice == "1":
                self.drivers.create_restore_point()
            elif choice == "2":
                report = RunReport()
                ok, reboot = self.drivers.update_drivers()
                report.driver_success = ok
                report.reboot_required = reboot
                self._print_summary(report)
            elif choice == "3":
                upgrades = self.app.list_upgrades()
                if upgrades:
                    chosen = self.selector.loop(upgrades, self.app, title="Upgradable Apps (winget)")
                else:
                    self.console.warn("No upgrades detected by winget.")
                    self.console.info("Showing installed apps so you can pick targets by Id.")
                    installed = self.app.list_installed()
                    if not installed:
                        self.console.warn("Could not read installed apps. Try updating winget (App Installer).")
                        continue
                    chosen = self.selector.loop(installed, self.app, title="Installed Apps (select any to attempt upgrade)")
                if chosen:
                    self.console.header("Update Plan (per-package)")
                    for pid in chosen: print(f"{GREEN}✔ {pid}{RESET}")
                    print()
                    confirm = input(f"{ORANGE1}{BOLD}Proceed with these updates? (y/N) {RESET}").strip().lower()
                    if confirm == "y":
                        r = RunReport()
                        res = self.app.update_ids(chosen)
                        r.updated.extend(res["updated"])
                        r.interactive.extend(res["interactive"])
                        r.reinstalled.extend(res["reinstalled"])
                        r.skipped.extend(res["skipped"])
                        r.store_skipped.extend(res["store_skipped"])
                        r.failed.extend(res["failed"])
                        self._print_summary(r)
            elif choice == "4":
                self.system.cleanup_temp(); self.system.empty_recycle_bin()
            elif choice == "5":
                self.system.dism_sfc()
            elif choice == "6":
                self.system.show_startup()
            elif choice == "7":
                r = RunReport()
                self.drivers.create_restore_point("Sensei_Quick_RP")
                ok, reboot = self.drivers.update_drivers()
                r.driver_success = ok
                r.reboot_required = reboot
                upgrades = self.app.list_upgrades()
                if upgrades:
                    res = self.app.update_ids([p["Id"] for p in upgrades])
                    r.updated.extend(res["updated"])
                    r.interactive.extend(res["interactive"])
                    r.reinstalled.extend(res["reinstalled"])
                    r.skipped.extend(res["skipped"])
                    r.store_skipped.extend(res["store_skipped"])
                    r.failed.extend(res["failed"])
                self.system.cleanup_temp(); self.system.empty_recycle_bin()
                self.console.header("Quick Maintenance")
                self.console.ok("All quick tasks completed. If drivers were installed, consider rebooting.")
                self._print_summary(r)
            elif choice == "0":
                print(f"{RED}{BOLD}Bye!{RESET}")
                break
            else:
                self.console.warn("Invalid choice. Try again.")