#!/usr/bin/env python3
# Sensei's Updater — safe, clean, class-based Windows maintenance
# Features:
#   - Update drivers via Windows Update (Drivers category) — robust across PSWindowsUpdate versions
#   - Update apps via winget with dynamic selection; resilient to localized/plain output
#   - Create a restore point; clean TEMP & Recycle Bin; run DISM/SFC; show startup apps
#   - UTF-8 + ANSI console support to avoid encoding issues
#   - Pixel art shown automatically (no menu option)
#   - Runs in User OR Admin context; enforces admin only for actions that need it
#   - Flags: --quick --drivers --apps --cleanup --health --startup --dry-run --debug
#
# Notes:
#   - Drivers/cleanup/health need an elevated (Administrator) terminal.
#   - Microsoft Store app updates require a NON-admin terminal.
#   - Profiles are saved to: %LOCALAPPDATA%\SenseiUpdater\config.json

import os
import sys
import re
import json
import shutil
import subprocess
import ctypes
import tempfile
from pathlib import Path

# ---------------------------
# Constants and flags
# ---------------------------
IS_WINDOWS = (os.name == "nt")
ARGS = set(a.lower() for a in sys.argv[1:])
DRY_RUN = ("--dry-run" in ARGS)
DEBUG = ("--debug" in ARGS)

APP_NAME = "SenseiUpdater"
CONFIG_DIR = Path(os.getenv("LOCALAPPDATA", Path.home())) / APP_NAME
CONFIG_PATH = CONFIG_DIR / "config.json"
KO_FI_URL = "https://ko-fi.com/senseiissei"

# ---------------------------
# ANSI colors
# ---------------------------
RESET   = "\x1b[0m"
BOLD    = "\x1b[1m"
DIM     = "\x1b[2m"
RED     = "\x1b[31m"
GREEN   = "\x1b[32m"
YELLOW  = "\x1b[33m"
MAGENTA = "\x1b[35m"
CYAN    = "\x1b[36m"

def C256(n: int) -> str:
    return f"\x1b[38;5;{n}m"
ORANGE2 = C256(208)
ORANGE1 = C256(214)
SUN     = C256(226)
BROWN   = C256(94)
AMBER   = C256(178)
GRAY    = C256(245)
WHITE   = C256(255)

# ---------------------------
# Core class
# ---------------------------
class SenseisUpdater:
    def __init__(self, dry_run: bool = False, debug: bool = False):
        self.dry_run = dry_run
        self.debug = debug

    # ----- Utilities -----
    def is_admin(self) -> bool:
        if not IS_WINDOWS:
            return False
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def enable_windows_ansi_utf8(self):
        """Enable ANSI + UTF-8 console on Windows to avoid encoding issues."""
        if not IS_WINDOWS:
            return
        try:
            kernel32 = ctypes.windll.kernel32
            hOut = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(hOut, ctypes.byref(mode)):
                kernel32.SetConsoleMode(hOut, mode.value | 0x0004)
            kernel32.SetConsoleOutputCP(65001)
            kernel32.SetConsoleCP(65001)
        except Exception:
            pass

    def print_header(self, title: str):
        print(f"{ORANGE2}{BOLD}{'=' * 80}{RESET}")
        print(f"{ORANGE2}{BOLD}{title}{RESET}")
        print(f"{ORANGE2}{BOLD}{'=' * 80}{RESET}")

    def info(self, msg: str): print(f"{CYAN}→ {msg}{RESET}")
    def ok(self, msg: str):   print(f"{GREEN}✔ {msg}{RESET}")
    def warn(self, msg: str): print(f"{YELLOW}⚠ {msg}{RESET}")
    def err(self, msg: str):  print(f"{RED}{BOLD}✘ {msg}{RESET}")

    def banner(self):
        ctx = "Administrator" if self.is_admin() else "User"
        ctx_color = RED if self.is_admin() else GREEN
        print(f"\n{SUN}{BOLD}Sensei's Updater{RESET}  {GRAY}— clean • update • repair (safely){RESET}")
        print(f"{ctx_color}{BOLD}Context:{RESET} {ctx}\n")
        print(f"{GRAY}If you enjoy the updater, you can support me: {WHITE}{BOLD}{KO_FI_URL}{RESET}\n")

    def pixel_art_pikachu(self):
        art = [
            f"{GRAY}{DIM}                 ..:::{RESET}{BROWN}▀▀▀▀▀▀{RESET}{GRAY}{DIM}:::..                 {RESET}",
            f"{GRAY}{DIM}             ..:::{RESET}{BROWN}▀▀▀{RESET}{SUN}{BOLD}▀▀{RESET}{BROWN}▀▀▀{RESET}{GRAY}{DIM}:::..             {RESET}",
            f"           {BROWN}▄{SUN}████████{BROWN}▄{SUN}████████{BROWN}▄{RESET}",
            f"         {BROWN}▄{SUN}██████████████████████{BROWN}▄{RESET}",
            f"       {BROWN}▄{SUN}████{BROWN}▄{SUN}████████████████{BROWN}▄{SUN}████{BROWN}▄{RESET}",
            f"      {BROWN}█{SUN}██{BROWN}█{SUN}██{BROWN}█  {RESET}{WHITE}{BOLD}●{RESET}{SUN}██████{WHITE}{BOLD}●{RESET}{SUN}  {BROWN}█{SUN}██{BROWN}█{SUN}██{BROWN}█{RESET}",
            f"      {BROWN}█{SUN}██{BROWN}█{SUN}██{BROWN}█ {RESET}{ORANGE1}{BOLD}●{RESET}{SUN}████████{ORANGE1}{BOLD}●{RESET}{SUN} {BROWN}█{SUN}██{BROWN}█{SUN}██{BROWN}█{RESET}",
            f"      {BROWN}█{SUN}████████  {RED}{BOLD}▂▂{RESET}{SUN}  {RED}{BOLD}▂▂{RESET}{SUN}  ████{BROWN}█{RESET}",
            f"       {BROWN}▀{SUN}██████████████████████{BROWN}▀{RESET}",
            f"          {BROWN}▄{SUN}██{BROWN}▄       {SUN}██       {BROWN}▄{SUN}██{BROWN}▄{RESET}",
            f"         {BROWN}█{SUN}███████{AMBER}██████████{SUN}███████{BROWN}█{RESET}",
            f"        {BROWN}█{SUN}██{BROWN}▄  {SUN}███{BROWN}▄      ▄{SUN}███  {BROWN}▄{SUN}██{BROWN}█{RESET}",
            f"        {BROWN}▀{SUN}██{BROWN}▀   {SUN}██{BROWN}▀      ▀{SUN}██   {BROWN}▀{SUN}██{BROWN}▀{RESET}",
            ""
        ]
        print("\n".join(art))

    # ----- Regex helpers -----
    def _looks_like_version(self, s: str) -> bool:
        return bool(re.fullmatch(r"[0-9]+(\.[0-9A-Za-z\-+]+)+", s or ""))

    def _looks_like_id(self, s: str) -> bool:
        return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-\._]+[A-Za-z0-9]", s or "")) and (" " not in s) and ("." in s)

    # ----- Subprocess helpers -----
    def run_stream(self, cmd):
        if self.debug:
            print(f"{MAGENTA}{DIM}>>> {' '.join(cmd)}{RESET}")
        if self.dry_run:
            self.warn(f"DRY-RUN: would run: {' '.join(cmd)}")
            return 0
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                if line.strip().startswith("VERBOSE:"):
                    print(f"{GRAY}{line.rstrip()}{RESET}")
                else:
                    print(line, end="")
            return proc.wait()
        except KeyboardInterrupt:
            try: proc.terminate()
            except Exception: pass
            return 1

    def run_capture(self, cmd):
        if self.debug:
            print(f"{MAGENTA}{DIM}>>> {' '.join(cmd)}{RESET}")
        if self.dry_run:
            self.warn(f"DRY-RUN: would run: {' '.join(cmd)}")
            return 0, ""
        res = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            shell=False
        )
        return res.returncode, res.stdout

    def run_powershell_script(self, ps_code: str):
        """Run PowerShell with UTF-8 output enforced."""
        pwsh = "powershell.exe"
        ps_prefix = r'''
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
'''
        full_ps = ps_prefix + "\n" + ps_code
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ps1", mode="w", encoding="utf-8") as f:
            f.write(full_ps)
            ps1 = f.name
        cmd = [pwsh, "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", ps1]
        try:
            return self.run_stream(cmd)
        finally:
            try: os.remove(ps1)
            except Exception: pass

    # ----- Config -----
    def ensure_config_dir(self):
        try: CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        except Exception: pass

    def load_config(self):
        self.ensure_config_dir()
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_config(self, cfg: dict):
        self.ensure_config_dir()
        tmp = CONFIG_PATH.with_suffix(".tmp.json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        tmp.replace(CONFIG_PATH)

    def profile_list(self, cfg):
        return sorted(cfg.get("profiles", {}).keys())

    def profile_get(self, cfg, name: str):
        return set(cfg.get("profiles", {}).get(name, []))

    def profile_set(self, cfg, name: str, package_ids):
        cfg.setdefault("profiles", {})[name] = sorted(set(package_ids))
        self.save_config(cfg)

    # ----- Admin-required helpers -----
    def demand_admin_or_explain(self, action_name: str):
        if self.is_admin():
            return True
        self.err(f"{action_name} requires Administrator.")
        self.info("Close this window, re-open Terminal/PowerShell as Administrator, and run again.")
        return False

    # ----- Actions -----
    def ensure_pswindowsupdate_installed(self):
        self.print_header("Preparing PowerShell + PSWindowsUpdate")
        self.info("Trusting PSGallery and installing NuGet + PSWindowsUpdate (if needed)...")
        ps = r'''
if (-not (Get-PackageProvider -Name NuGet -ListAvailable -ErrorAction SilentlyContinue)) {
  Install-PackageProvider -Name NuGet -Force -Scope AllUsers | Out-Null
}
try {
  $repo = Get-PSRepository -Name "PSGallery" -ErrorAction Stop
  if ($repo.InstallationPolicy -ne "Trusted") {
    Set-PSRepository -Name "PSGallery" -InstallationPolicy Trusted
  }
} catch {
  Register-PSRepository -Name "PSGallery" -SourceLocation "https://www.powershellgallery.com/api/v2" -InstallationPolicy Trusted
}
if (-not (Get-Module -ListAvailable -Name PSWindowsUpdate)) {
  Install-Module -Name PSWindowsUpdate -Force -Scope AllUsers -AllowClobber | Out-Null
}
Import-Module PSWindowsUpdate -Force
Write-Host "PSWindowsUpdate is ready."
'''
        rc = self.run_powershell_script(ps)
        if rc != 0:
            self.err("Failed to prepare PSWindowsUpdate. Aborting driver update.")
            sys.exit(1)
        else:
            self.ok("PSWindowsUpdate is ready.")

    def create_restore_point(self, description: str = "Sensei_Restore_Point"):
        if not self.demand_admin_or_explain("Create Restore Point"):
            return
        self.print_header("Create System Restore Point")
        ps = f'''
try {{
  Checkpoint-Computer -Description "{description}" -RestorePointType "MODIFY_SETTINGS"
  Write-Host "Restore point created."
}} catch {{
  Write-Warning "Could not create restore point: $($_.Exception.Message)"
}}
'''
        rc = self.run_powershell_script(ps)
        if rc == 0: self.ok("Restore point created (or one already exists today).")
        else:       self.warn("Could not create a restore point. (Is System Protection enabled?)")

    def update_drivers(self):
        if not self.demand_admin_or_explain("Driver Updates"):
            return
        self.print_header("Driver Updates via Windows Update (Drivers category)")
        self.ensure_pswindowsupdate_installed()
        self.info("Scanning Windows Update for driver updates... (this can take a while)")
        ps = r'''
Import-Module PSWindowsUpdate -Force
try { Add-WUServiceManager -MicrosoftUpdate -Confirm:$false | Out-Null } catch { }

$drivers = $null
try {
  $drivers = Get-WindowsUpdate -MicrosoftUpdate -Category 'Drivers' -Verbose -ErrorAction Stop
} catch {
  if (Get-Command Get-WUList -ErrorAction SilentlyContinue) {
    $drivers = Get-WUList -MicrosoftUpdate -Category Drivers -Verbose
  } else { throw }
}

if ($drivers -and $drivers.Count -gt 0) {
  Write-Host "Driver updates found:"
  $drivers | Select-Object Title, KB, Size | Format-Table -AutoSize
  Write-Host "Installing driver updates..."
  $installed = $false
  try {
    Install-WindowsUpdate -MicrosoftUpdate -Category 'Drivers' -AcceptAll -AutoReboot:$false -Verbose
    $installed = $true
  } catch {
    try {
      Install-WindowsUpdate -MicrosoftUpdate -Category Drivers -AcceptAll -IgnoreReboot -Verbose
      $installed = $true
    } catch {
      Write-Warning ("Install-WindowsUpdate failed: " + $_.Exception.Message)
    }
  }
  if ($installed) { Write-Host "Driver updates completed. A reboot may be required." }
  else { Write-Warning "Could not install driver updates. See messages above." }
} else {
  Write-Host "No driver updates available."
}
'''
        rc = self.run_powershell_script(ps)
        if rc == 0: self.ok("Driver update step finished.")
        else:       self.err("Driver update step failed (see output above).")

    def empty_recycle_bin(self):
        if not self.demand_admin_or_explain("Empty Recycle Bin"):
            return
        self.print_header("Emptying Recycle Bin")
        ps = r'''
try {
  Clear-RecycleBin -Force -ErrorAction SilentlyContinue
  Write-Host "Recycle Bin emptied (or already empty)."
} catch {
  Write-Warning "Failed to empty Recycle Bin: $($_.Exception.Message)"
}
'''
        rc = self.run_powershell_script(ps)
        if rc == 0: self.ok("Recycle Bin emptied.")
        else:       self.warn("Could not empty Recycle Bin.")

    def cleanup_temp(self):
        if not self.demand_admin_or_explain("Clean TEMP folders"):
            return
        self.print_header("Cleaning TEMP folders")
        candidates = set()
        for env_var in ("TEMP", "TMP"):
            p = os.environ.get(env_var)
            if p: candidates.add(Path(p))
        candidates.add(Path(r"C:\Windows\Temp"))
        deleted = 0
        for root in candidates:
            try:
                if root.exists():
                    for item in root.iterdir():
                        try:
                            if item.is_file() or item.is_symlink():
                                if not self.dry_run:
                                    item.unlink(missing_ok=True)
                                deleted += 1
                            elif item.is_dir():
                                if not self.dry_run:
                                    shutil.rmtree(item, ignore_errors=True)
                                deleted += 1
                        except Exception:
                            pass
            except Exception:
                pass
        self.ok(f"Removed ~{deleted} temp items (best effort).")

    def dism_sfc_health(self):
        if not self.demand_admin_or_explain("System Health (DISM + SFC)"):
            return
        self.print_header("System Health: DISM + SFC")
        self.info("Running: DISM /Online /Cleanup-Image /ScanHealth")
        self.run_stream(["DISM", "/Online", "/Cleanup-Image", "/ScanHealth"])
        self.info("Running: DISM /Online /Cleanup-Image /RestoreHealth")
        self.run_stream(["DISM", "/Online", "/Cleanup-Image", "/RestoreHealth"])
        self.info("Running: SFC /scannow")
        self.run_stream(["sfc", "/scannow"])
        self.ok("Health scan completed. Review output above for any repairs.")

    def show_startup(self):
        self.print_header("Startup Programs")
        ps = r'''
Get-CimInstance Win32_StartupCommand |
  Select-Object Name, Command, Location |
  Sort-Object Name |
  Format-Table -AutoSize
'''
        self.run_powershell_script(ps)

    # ----- winget parsers/helpers -----
    def _parse_table_generic(self, text: str):
        """Robust parser for localized winget table output. Returns list of {Name, Id, Version, Available, Source}."""
        lines = [ln.rstrip() for ln in (text or "").splitlines()]
        rows = []
        for ln in lines:
            s = ln.strip()
            if not s:
                continue
            l = s.lower()
            if l.startswith("found ") or l.startswith("the following") or l.startswith("no "):
                continue
            cols = re.split(r"\s{2,}", s)
            if len(cols) < 2:
                continue

            name = cols[0]
            if len(cols) >= 2 and self._looks_like_id(cols[1]) and not self._looks_like_version(cols[1]):
                pid = cols[1]
                version  = cols[2] if len(cols) >= 3 else ""
                available= cols[3] if len(cols) >= 4 else ""
                source   = cols[4] if len(cols) >= 5 else ""
            elif len(cols) >= 3 and self._looks_like_version(cols[1]) and self._looks_like_id(cols[2]):
                pid = cols[2]
                version  = cols[1]
                available= cols[3] if len(cols) >= 4 else ""
                source   = cols[4] if len(cols) >= 5 else ""
            else:
                pid = ""
                version = ""
                available = ""
                source = ""
                for c in cols[1:]:
                    if not pid and self._looks_like_id(c) and not self._looks_like_version(c):
                        pid = c
                    elif not version and self._looks_like_version(c):
                        version = c
                    elif not available and self._looks_like_version(c):
                        available = c
                    elif not source and c.lower() in ("winget", "msstore", "store", "msix", "msi", "exe"):
                        source = c
            if not pid:
                continue
            rows.append({"Name": name, "Id": pid, "Version": version, "Available": available, "Source": source})

        dedup = {}
        for r in rows:
            dedup[r["Id"]] = r
        return list(dedup.values())

    def winget_check_json_support(self):
        rc, _ = self.run_capture(["winget", "--version"])
        if rc != 0:
            self.err("winget not found. Install 'App Installer' from Microsoft Store.")
            return False
        rc, out = self.run_capture(["winget", "upgrade", "--output", "json"])
        s = (out or "").strip()
        return (rc == 0) and (s.startswith("{") or s.startswith("["))

    def _winget_list_upgrades_plain(self):
        variants = [
            ["winget", "upgrade"],
            ["winget", "upgrade", "--include-unknown"],
            ["winget", "upgrade", "--source", "winget"],
            ["winget", "upgrade", "--source", "msstore"],
        ]
        for cmd in variants:
            rc, out = self.run_capture(cmd)
            if rc == 0 and out:
                rows = self._parse_table_generic(out)
                if rows:
                    return rows
        return []

    def _winget_list_installed_plain(self):
        variants = [
            ["winget", "list"],
            ["winget", "list", "--source", "winget"],
            ["winget", "list", "--source", "msstore"],
        ]
        for cmd in variants:
            rc, out = self.run_capture(cmd)
            if rc == 0 and out:
                rows = self._parse_table_generic(out)
                rows = [r for r in rows if self._looks_like_id(r.get("Id",""))]
                if rows:
                    return rows
        return []

    def winget_list_upgrades(self):
        """Try JSON first; if unsupported, parse plain `upgrade`."""
        if self.winget_check_json_support():
            rc, out = self.run_capture(["winget", "upgrade", "--output", "json"])
            if rc == 0 and out:
                try:
                    data = json.loads(out)
                    pkgs = []
                    if isinstance(data, dict) and "InstalledPackages" in data:
                        for p in data.get("InstalledPackages", []):
                            pkgs.append({
                                "Id": p.get("PackageIdentifier") or p.get("Id") or "",
                                "Name": p.get("PackageName") or p.get("Name") or "",
                                "Version": p.get("InstalledVersion") or p.get("Version") or "",
                                "Available": p.get("AvailableVersion") or p.get("Available") or "",
                                "Source": p.get("Source") or "",
                            })
                    elif isinstance(data, list):
                        for p in data:
                            pkgs.append({
                                "Id": p.get("PackageIdentifier") or p.get("Id") or "",
                                "Name": p.get("PackageName") or p.get("Name") or "",
                                "Version": p.get("InstalledVersion") or p.get("Version") or "",
                                "Available": p.get("AvailableVersion") or p.get("Available") or "",
                                "Source": p.get("Source") or "",
                            })
                    return [x for x in pkgs if x["Id"]]
                except json.JSONDecodeError:
                    pass
        return self._winget_list_upgrades_plain()

    # ----- App selector UI -----
    def print_pkg_table(self, pkgs, selected_ids=None, title="Upgradable Apps (winget)"):
        if selected_ids is None:
            selected_ids = set()
        self.print_header(title)
        if not pkgs:
            self.warn("No entries found.")
            return
        w_idx = len(str(len(pkgs)))
        print(f"{ORANGE1}{BOLD}{'#'.rjust(w_idx)}  {'Sel':3}  {'Name':40}  {'Id':34}  {'Installed':>12}  {'Available':>12}  {'Src':4}{RESET}")
        for i, p in enumerate(pkgs, 1):
            sel = "✔" if p["Id"] in selected_ids else " "
            name = (p.get("Name",""))[:40].ljust(40)
            pid  = (p.get("Id",""))[:34].ljust(34)
            ver  = (p.get("Version",""))[:12].rjust(12)
            avail= (p.get("Available",""))[:12].rjust(12)
            src  = (p.get("Source",""))[:4].ljust(4)
            color = GREEN if sel == "✔" else GRAY
            print(f"{SUN}{str(i).rjust(w_idx)}{RESET}   {color}{sel:3}{RESET}  {WHITE}{name}{RESET}  {GRAY}{pid}{RESET}  {ver}  {avail}  {src}")

    def selector_loop(self, pkgs, cfg, title):
        selected = set()
        while True:
            self.pixel_art_pikachu()
            self.print_pkg_table(pkgs, selected, title=title)
            print()
            print(f"{ORANGE1}{BOLD}Commands{RESET}: numbers (e.g. 1,3,5) | all | none |")
            print("  filter <text>      — show rows containing text")
            print("  search <text>      — search winget catalog; then use 'add <id>'")
            print("  add <id>           — add package id to selection")
            print("  rm <id>            — remove package id from selection")
            print("  u <id>             — update a single id immediately")
            print("  u all              — update all currently selected")
            print("  load <name>        — load saved selection")
            print("  save <name>        — save current selection")
            print("  profiles           — list saved profiles")
            print("  go                 — proceed to update selected")
            print("  back               — return to main menu")
            cmd = input(f"{ORANGE2}{BOLD}Select → {RESET}").strip()

            if not cmd:
                continue
            if cmd == "back":
                return None
            if cmd == "all":
                selected = {p["Id"] for p in pkgs if p["Id"]}
                self.ok(f"Selected ALL ({len(selected)})")
                continue
            if cmd == "none":
                selected.clear()
                self.ok("Cleared selection.")
                continue
            if cmd.startswith("filter "):
                q = cmd[len("filter "):].strip().lower()
                flt = [p for p in pkgs if q in (p.get("Name","").lower()) or q in (p.get("Id","").lower())]
                self.print_pkg_table(flt, selected, title=f"Filtered: '{q}'")
                continue
            if cmd.startswith("search "):
                q = cmd[len("search "):].strip()
                if not q:
                    self.warn("Provide search text, e.g. search vscode")
                    continue
                rc, out = self.run_capture(["winget", "search", q])
                if rc == 0 and out:
                    rows = self._parse_table_generic(out)
                    if rows:
                        self.print_pkg_table(rows, title="Search results (winget catalog)")
                        print(f"{GRAY}Tip: use 'add <id>' to add any of these ids to your selection.{RESET}")
                    else:
                        self.warn("No search results.")
                else:
                    self.warn("Search failed.")
                continue
            if cmd.startswith("add "):
                pid = cmd[len("add "):].strip()
                if pid:
                    if self._looks_like_id(pid) and not self._looks_like_version(pid):
                        selected.add(pid)
                        self.ok(f"Added: {pid}")
                    else:
                        self.warn(f"Not a valid package Id: {pid}")
                continue
            if cmd.startswith("rm "):
                pid = cmd[len("rm "):].strip()
                if pid in selected:
                    selected.remove(pid)
                    self.ok(f"Removed: {pid}")
                continue
            if cmd == "profiles":
                names = self.profile_list(cfg)
                if not names:
                    self.warn("No saved profiles.")
                else:
                    self.info("Profiles: " + ", ".join(names))
                continue
            if cmd.startswith("load "):
                name = cmd[len("load "):].strip()
                s = self.profile_get(cfg, name)
                if not s:
                    self.warn(f"No saved profile named '{name}'.")
                else:
                    selected = set(s)
                    self.ok(f"Loaded profile '{name}' with {len(selected)} entries.")
                continue
            if cmd.startswith("save "):
                name = cmd[len("save "):].strip()
                if not name:
                    self.warn("Please provide a profile name.")
                else:
                    self.profile_set(cfg, name, selected)
                    self.ok(f"Saved profile '{name}' with {len(selected)} entries.")
                continue
            if cmd.startswith("u "):
                arg = cmd[len("u "):].strip()
                if arg == "all":
                    self._apply_updates(list(selected))
                else:
                    if not arg:
                        self.warn("Usage: u <id>  |  u all")
                    else:
                        self._apply_updates([arg])
                continue
            if cmd == "go":
                if not selected:
                    self.warn("No packages selected.")
                    continue
                return list(selected)
            try:
                indices = [int(x.strip()) for x in cmd.split(",") if x.strip().isdigit()]
                changed = 0
                for idx in indices:
                    if 1 <= idx <= len(pkgs):
                        pid = pkgs[idx-1]["Id"]
                        if pid:
                            if pid in selected: selected.remove(pid)
                            else: selected.add(pid)
                            changed += 1
                self.ok(f"Toggled {changed} package(s).")
            except Exception:
                self.warn("Unknown command. Try: 1,3,5  |  all  |  none  |  search vscode  |  add <id>  |  go")

    def _apply_updates(self, ids):
        if not ids:
            self.warn("Nothing to update.")
            return
        self.print_header("Installing selected app updates (winget)")

        id_to_source = {}
        rc, out = self.run_capture(["winget", "upgrade"])
        if rc == 0 and out:
            for r in self._parse_table_generic(out):
                id_to_source[r["Id"]] = (r.get("Source","") or "").lower()

        user_context = not self.is_admin()

        for pid in ids:
            if not self._looks_like_id(pid) or self._looks_like_version(pid):
                self.warn(f"Skipping invalid Id (looks like a version or malformed): {pid}")
                continue

            src = id_to_source.get(pid, "")

            cmd = ["winget", "upgrade", "--id", pid, "--accept-package-agreements", "--accept-source-agreements"]
            if src in ("msstore", "store"):
                if not user_context:
                    self.warn(f"{pid} is a Microsoft Store app. Run this tool in a NON-admin terminal and retry.")
                    continue
                cmd += ["--source", "msstore"]
            cmd_silent = cmd + ["--silent"]

            self.info(f"Updating {pid} ...")
            rc = self.run_stream(cmd_silent)
            if rc == 0:
                self.ok(f"Updated (or already current): {pid}")
                continue

            if src in ("msstore", "store"):
                self.warn(f"{pid}: Store upgrade failed. Open Microsoft Store → Library → Get updates.")
                continue

            self.info(f"{pid}: retrying in interactive mode…")
            cmd_interactive = [c for c in cmd if c != "--silent"] + ["--interactive"]
            rc2 = self.run_stream(cmd_interactive)
            if rc2 == 0:
                self.ok(f"Updated interactively: {pid}")
            else:
                self.info(f"{pid}: trying reinstall as last resort…")
                rc3 = self.run_stream(["winget", "install", "--id", pid,
                                       "--accept-package-agreements", "--accept-source-agreements", "--silent"])
                if rc3 == 0:
                    self.ok(f"Reinstalled: {pid}")
                else:
                    self.warn(f"Failed or not applicable: {pid}")

    def update_apps_selector(self):
        cfg = self.load_config()
        upgrades = self.winget_list_upgrades()
        if upgrades:
            chosen_ids = self.selector_loop(upgrades, cfg, title="Upgradable Apps (winget)")
        else:
            self.warn("No upgrades detected by winget.")
            self.info("Showing installed apps so you can pick targets by Id (winget will skip ones already current).")
            self.info("Tip: For Microsoft Store apps (Source=msstore), run this tool WITHOUT admin for the update step.")
            installed = self._winget_list_installed_plain()
            if not installed:
                self.warn("Could not read installed apps either. Try updating winget (App Installer).")
                return
            chosen_ids = self.selector_loop(installed, cfg, title="Installed Apps (select any to attempt upgrade)")
        if not chosen_ids:
            self.info("No changes made.")
            return

        self.print_header("Update Plan (per-package)")
        for pid in chosen_ids:
            print(f"{GREEN}✔ {pid}{RESET}")
        print()
        confirm = input(f"{ORANGE1}{BOLD}Proceed with these updates? (y/N) {RESET}").strip().lower()
        if confirm != "y":
            self.warn("Aborted by user.")
            return
        self._apply_updates(chosen_ids)

    # ----- Orchestrations -----
    def quick_maintenance(self):
        if not self.demand_admin_or_explain("Quick Maintenance"):
            return
        self.create_restore_point("Sensei_Quick_RP")
        self.update_drivers()
        self.update_apps_selector()
        self.cleanup_temp()
        self.empty_recycle_bin()
        self.print_header("Quick Maintenance")
        self.ok("All quick tasks completed. If drivers were installed, consider rebooting.")

    def interactive_menu(self):
        while True:
            self.pixel_art_pikachu()
            ctx = "Administrator" if self.is_admin() else "User"
            print(f"{GRAY}Context: {ctx}  •  Run apps updates as User; run drivers/cleanup/health as Admin.{RESET}")
            self.print_header("Sensei's Updater — Menu")
            print(f"{ORANGE1}{BOLD}1){RESET} Create Restore Point  {GRAY}(Admin){RESET}")
            print(f"{ORANGE1}{BOLD}2){RESET} Update Drivers (Windows Update — Drivers)  {GRAY}(Admin){RESET}")
            print(f"{ORANGE1}{BOLD}3){RESET} Update Applications (choose dynamically)  {GRAY}(User recommended){RESET}")
            print(f"{ORANGE1}{BOLD}4){RESET} Cleanup TEMP + Empty Recycle Bin  {GRAY}(Admin){RESET}")
            print(f"{ORANGE1}{BOLD}5){RESET} Health Scan (DISM + SFC)  {GRAY}(Admin){RESET}")
            print(f"{ORANGE1}{BOLD}6){RESET} Show Startup Programs")
            print(f"{ORANGE1}{BOLD}7){RESET} QUICK: 1+2+3+4 in one go  {GRAY}(Admin){RESET}")
            print(f"{RED}{BOLD}0){RESET} Exit")
            choice = input(f"{ORANGE2}{BOLD}Select → {RESET}").strip()
            if choice == "1":
                self.create_restore_point()
            elif choice == "2":
                self.update_drivers()
            elif choice == "3":
                self.update_apps_selector()
            elif choice == "4":
                self.cleanup_temp(); self.empty_recycle_bin()
            elif choice == "5":
                self.dism_sfc_health()
            elif choice == "6":
                self.show_startup()
            elif choice == "7":
                self.quick_maintenance()
            elif choice == "0":
                print(f"{RED}{BOLD}Bye!{RESET}")
                break
            else:
                self.warn("Invalid choice. Try again.")

# ---------------------------
# Entrypoint
# ---------------------------
def main():
    app = SenseisUpdater(dry_run=DRY_RUN, debug=DEBUG)
    app.enable_windows_ansi_utf8()
    app.banner()

    if "--quick"   in ARGS: app.quick_maintenance(); return
    if "--drivers" in ARGS: app.update_drivers();     return
    if "--apps"    in ARGS: app.update_apps_selector(); return
    if "--cleanup" in ARGS: app.cleanup_temp(); app.empty_recycle_bin(); return
    if "--health"  in ARGS: app.dism_sfc_health();    return
    if "--startup" in ARGS: app.show_startup();       return

    app.interactive_menu()

if __name__ == "__main__":
    main()