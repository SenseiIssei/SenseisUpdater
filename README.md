# Sensei’s Updater — Free Windows Driver & Software Updater (Windows 10/11)

A safe, colorized **Windows updater** that helps you **update drivers** and **update software** on Windows 10/11—powered by Microsoft’s **Windows Update** (Drivers category) and **winget** for application updates. It also includes one-click maintenance: **System Restore Point**, **TEMP cleanup**, **Recycle Bin empty**, **DISM/SFC** system health checks, and a **Startup programs** viewer. No bloat, no ads—just a clean CLI with a little pixel art flair.

> ❤️ Enjoying the updater? Buy me a coffee: **https://ko-fi.com/senseiissei**

---

## Highlights

- ✅ **Windows Driver Updater** via Windows Update *(Drivers category; robust across PSWindowsUpdate versions)*
- ✅ **Windows Software Updater** via `winget` with **dynamic selection**, search, and **profiles**
- ✅ **Admin-gated** tasks (Drivers, DISM/SFC, Cleanup) & **User-mode** for Microsoft Store app updates
- ✅ **Safe defaults**: creates **Restore Point**, UTF-8 console, defensive parsing, clear prompts
- ✅ **Fast & friendly**: retry **interactive** when needed; reinstall fallback; clear colorized output
- ✅ **Portable EXE**: build a single file with **PyInstaller** (GitHub Actions / GitLab CI included)

> This project emphasizes **safety, clarity, and Windows-native tooling**. It is *not* a kernel-mode driver packer; it relies on **Windows Update** for drivers and **winget** for software packages.

---

## Table of Contents

- [Why choose Sensei’s Updater?](#why-choose-senseis-updater)
- [What it can do](#what-it-can-do)
- [Requirements](#requirements)
- [Install & Run (from source)](#install--run-from-source)
- [Build a Portable EXE](#build-a-portable-exe)
- [Usage Guide](#usage-guide)
  - [Admin vs User Context](#admin-vs-user-context)
  - [Flags / CLI Options](#flags--cli-options)
  - [App Selection Tips (winget)](#app-selection-tips-winget)
- [Troubleshooting](#troubleshooting)
- [Security & Privacy](#security--privacy)
- [CI: GitHub Actions & GitLab CI](#ci-github-actions--gitlab-ci)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)
- [SEO Keywords (for discoverability)](#seo-keywords-for-discoverability)

---

## Roadmap

This is our living plan for Sensei’s Updater. It focuses on safety, clarity, and Windows-native tooling. Items are grouped by timeframe, with high-level milestones and concrete tasks.

### Guiding Principles
- **Safety first:** no forced changes; clear prompts; restore point support.
- **Windows-native:** drivers via Windows Update; apps via winget.
- **Privacy by default:** no telemetry; any analytics must be explicit opt-in.
- **Clarity & UX:** helpful messages, colorized output, minimal friction.

---

### NOW (v1.x maintenance & UX polish)
- **Run summary & reports**
  - [ ] End-of-run summary (updated, skipped, failed, reboot required).
  - [ ] `--report json|txt` and `--out <path>` to export results.
- **Pending reboot detection**
  - [ ] Warn if Windows signals a required reboot before updates.
- **Profiles & non-interactive**
  - [ ] `--profile <name>` to auto-load a saved selection.
  - [ ] `--yes` to apply without extra confirmation (power users/CI).
- **Diagnostics (opt-in, local only)**
  - [ ] `--diagnostics` to create a zip (logs, versions, last report) for bug reports.
- **Robustness**
  - [ ] Timeouts + clearer errors around PowerShell/winget.
  - [ ] Smarter handling of Store apps (admin vs user context hints).
- **Docs**
  - [ ] Expand README troubleshooting, add GIF of the flow.
  - [ ] CONTRIBUTING guide with issue templates (bug/feature).

---

### NEXT (v2.0 usability leap)
- **Rich terminal UI (TUI)**
  - [ ] Migrate menu to a TUI (e.g., Textual / prompt_toolkit).
  - [ ] Scrollable table with filter/search/sort; multi-select with checkboxes.
  - [ ] Inline progress, status badges (Updated / Skipped / Needs input).
- **Scheduling (opt-in)**
  - [ ] `--schedule weekly|monthly` creates a Task Scheduler entry.
  - [ ] Logs to `%LOCALAPPDATA%\SenseiUpdater\logs\`.
- **Config file**
  - [ ] `%LOCALAPPDATA%\SenseiUpdater\settings.json` (default profile, color on/off, PowerShell 7 preference, timeouts).
- **Store integration helpers**
  - [ ] One-click open Microsoft Store Library for pending Store updates.
- **Export/Import selections**
  - [ ] `--export profile.json` / `--import profile.json` to share app sets.

---

### LATER (v3.x+ features & ecosystem)
- **GUI options**
  - [ ] TUI-in-a-window (WebView wrapper) for a lightweight “GUI feel”.
  - [ ] Full GUI (PySide6/Qt) as an optional download (larger EXE).
- **“Update All” policy engine (advanced users)**
  - [ ] Rules to include/exclude sources (winget/msstore), categories, or IDs.
  - [ ] Optional “silent only”; skip apps requiring interactive installers.
- **Enterprise-friendly switches**
  - [ ] Read-only audit mode `--audit` (no changes; JSON report for scripts).
  - [ ] Proxy settings; offline catalogs (where possible).
- **Rollback helpers**
  - [ ] Snapshot app list pre-update; guide to uninstall/reinstall on failures.
  - [ ] Driver rollback guidance (lean on Restore Points & Windows UI).
- **Localization**
  - [ ] i18n framework; start with EN → DE translations of messages.
- **Plugin surface (exploration)**
  - [ ] Optional modules for reporting, export formats, or additional checks.
- **Security**
  - [ ] Signed builds (code signing) for EXE distributions.
  - [ ] Supply chain: pinned PyInstaller, reproducible build notes.

---

### QUALITY, TESTS & CI
- **Automated checks**
  - [ ] Lints & type checks (ruff/mypy) on PRs.
  - [ ] Smoke tests on Windows runners (list upgrades; parse outputs).
- **CI pipelines**
  - [ ] GitHub Actions: build EXE artifacts on every push/tag.
  - [ ] GitLab CI: tagged release pipeline with attached EXE.
- **Release hygiene**
  - [ ] Changelog entries per release; semantic versioning.
  - [ ] Release notes with known issues, Store app guidance.

---

### Telemetry & Feedback (always opt-in)
- **No default telemetry.**  
  If we ever add usage metrics:
  - [ ] `--analytics opt-in` flag only (explicit, reversible).
  - [ ] Collect *only* count + app version + coarse OS version, no IDs.
  - [ ] Publicly document endpoint and publish raw counts for verification.

---

### NON-GOALS (what we won’t do)
- ❌ Install unsigned drivers or bypass Windows security.
- ❌ Replace Windows Update with third-party driver bundles.
- ❌ Silent background services or hidden updates.
- ❌ Collect personal/system identifiers without explicit opt-in.

---

### Versioning & Cadence
- **v1.x**: Stability and UX polish (reports, profiles, robustness).
- **v2.0**: TUI upgrade, scheduling, config, export/import.
- **v3.x**: Optional GUI builds, policy engine, enterprise options.
- **Cadence**: Aim for minor updates every 2–6 weeks; patch releases as needed.

---

### How to track progress
- We use GitHub issues with labels:
  - `type:feature`, `type:bug`, `type:ux`, `good first issue`, `help wanted`.
- Milestones reflect the **Now / Next / Later** buckets above.
- Feedback welcome in Discussions; diagnostics are manual and opt-in.

---

## Why choose Sensei’s Updater?

- **Windows-native & trustworthy**  
  Uses **Windows Update** (PSWindowsUpdate module) for **driver updates** and **winget** for **software updates**—no shady sources.

- **Granular control**  
  Pick exactly which apps to update. Save and load **profiles** (e.g., “work-apps”, “gaming-stack”).

- **Safe by design**  
  Create a **Restore Point** before changes. DISM/SFC health checks. No silent kernel changes.

- **Fast & friendly**  
  Clean CLI with color states, clear explanations, and meaningful fallbacks (interactive mode, reinstall).

- **Free & open source**  
  No ads, no tracking, no upsells.

---

## What it can do

- **Update Drivers on Windows 10/11** via Windows Update (Drivers category)
- **Update Apps** (desktop & Store) via `winget`
  - Dynamic selection UI
  - Search winget catalog (`search <text>`, then `add <id>`)
  - Save/load **profiles** (e.g., `save dev`, `load dev`)
- **System Maintenance**
  - **Create Restore Point**
  - **DISM**: Scan/Restore Health
  - **SFC**: System file integrity scan
  - **Cleanup**: TEMP folders + **Empty Recycle Bin**
  - **Startup programs**: review launch entries

> ⚠️ **Microsoft Store** apps must update in **User (non-admin)** context (Windows design).

---

## Requirements

- **Windows 10/11**
- **Python 3.9+** (for running from source)
- **App Installer** (provides `winget`)
- Internet connectivity to fetch updates
- Optional (for EXE builds): **PyInstaller**

---

## Install & Run (from source)

#### Clone
```powershell
git clone https://github.com/your-github-user/your-repo.git senseis-updater
cd senseis-updater
```
#### Optional virtualenv
```powershell
py -3 -m venv .venv
. .\.venv\Scripts\Activate.ps1
```
#### Install package
```powershell
py -3 -m pip install --upgrade pip
py -3 -m pip install -e .
```
#### Run
```powershell
python -m sensei_updater
```
#### or
```powershell
sensei-updater
```

## Build .\dist\SenseisUpdater.exe
```powershell
scripts\build_exe.ps1
```
## Manual with PyInstaller:
```powershell
py -3 -m pip install pyinstaller
py -3 -m PyInstaller --noconfirm --clean --onefile --name "SenseisUpdater" --console src/sensei_updater/app.py
## EXE → .\dist\SenseisUpdater.exe
```

---

## Usage Guide
When launched, you’ll see a simple menu.
Choose tasks by number or run targeted flags.

### Admin vs User Context
- Run as **Administrator** for:
    - **Driver Updates**
    - **DISM / SFC**
    - **TEMP cleanup + Empty Recycle Bin**
    - **Quick maintenance**

- Run **without admin** for:

    - **Microsoft Store** app updates (e.g., Spotify).
        Store packages cannot update in an elevated context.

The app auto-detects your context and guides you.

### Flags / CLI Options
```powershell
--quick     Quick maintenance batch (admin recommended)
--drivers   Driver updates only (admin)
--apps      App updates selector (user recommended)
--cleanup   Clean TEMP & empty Recycle Bin (admin)
--health    DISM + SFC (admin)
--startup   Show startup programs
--dry-run   Print commands without executing
--debug     Print executed commands
```
### Examples:
```powershell
# App updates in user context (supports Microsoft Store)
sensei-updater --apps

# Driver updates, DISM/SFC in admin context
sensei-updater --drivers
sensei-updater --health

# One-and-done quick run (admin)
sensei-updater --quick
```
### App Selection Tips (winget)

**Inside the selector:**

- `filter vscode` — filter shown rows
- `search obs` — search the winget catalog
- `add OBSProject.OBSStudio` — add a specific package ID
- `u all` **or** `u <id>` — update immediately
- `save gaming` / `load gaming` — manage profiles
- `go` — proceed with selected updates
- `back` — return to main menu

> The tool validates IDs and never confuses a **version** (e.g., `12.0.40664.0`) with a **package ID**.

---

## Troubleshooting
### “Installer can’t run in admin context” (Spotify, etc.)
Run the app without admin:
```powershell
# Non-admin terminal
sensei-updater --apps
```

#### Discord/other app won’t update silently
- The tool will retry interactive, then reinstall as a fallback. If it still fails, check vendor guidance.

#### winget missing
- Install/update App Installer from Microsoft Store, then re-open the terminal.

#### Driver updates show nothing
- Windows Update may have no driver updates at this time. Ensure Microsoft Update service is added; the tool handles this for you.

#### PowerShell errors / encoding issues
- The runner enforces UTF-8 and replaces undecodable characters—logs still display.

---

## Security & Privacy
- **No telemetry** or tracking.
- Uses **Windows Update** and **winget**—trusted, signed sources when available.
- System changes are **opt-in** and explained in plain English.
- **Restore Point** creation is offered to help you roll back.

---

## CI: GitHub Actions & GitLab CI
- **GitHub Actions** workflow (.github/workflows/build.yml) builds a **Windows EXE** and uploads it as an artifact.
- **GitLab CI** (.gitlab-ci.yml) builds on a **Windows runner** and **creates Releases** on tags—attaching the EXE.

To publish a release on GitLab:
```powershell
git tag v1.0.0
git push origin v1.0.0
```
---

## Roadmap
- Optional “update all” non-interactive mode
- Optional export of update logs (JSON)
- Extra maintenance tools (e.g., disk usage report)

---

## Contributing
PRs welcome! Please:
1. Keep changes focused and documented.
2. Preserve admin/user gating.
3. Test both Store and non-Store app updates.
4. Update CHANGELOG.md and bump version in src/sensei_updater/__init__.py.

---

## License
MIT — see LICENSE.

---

# Support
If this tool saved you time, consider supporting future updates ❤️
Ko-fi: https://ko-fi.com/senseiissei

---

## SEO Keywords (for discoverability)

> GitHub README content is indexed by search engines; these phrases help users find the project.

- Windows driver updater, free driver updater for Windows 11, update drivers Windows 10  
- Windows software updater, update apps on Windows, winget updater, Windows package manager  
- Windows maintenance tool, DISM SFC Windows, clean temp files Windows, empty recycle bin  
- Microsoft Store apps update, Spotify update Windows, Discord update Windows via winget  
- PSWindowsUpdate driver updates, Windows Update drivers category, safe driver update Windows  
- Open source Windows updater, portable EXE Windows updater, command line updater Windows

<!--
Extra keywords for SEO (hidden from view):
windows updater, driver updater windows 11, driver update tool, software update tool windows, windows 10 update apps,
update microsoft store apps cli, winget upgrade, update drivers via powershell, free updater, safe updater,
open source updater, windows maintenance, optimize windows
-->