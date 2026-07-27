# Changelog

All notable changes to Odysync will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Windows Update.** Odysync now installs Windows' own security, quality and
  Defender updates, not just drivers. Three backends over one shared Windows
  Update Agent wrapper: `windows-update` (security and quality),
  `windows-defender-update` (definitions) and `windows-feature-update`
  (version upgrades). Updates are classified by category **GUID**, never by
  name, because category names are localised.
- Feature upgrades are **off until opted into** by name in `enabled-backends`.
  Gating them through `BackendKind::enabled_by_default` rather than a default
  `disabled-backends` entry means the gate also applies to config files
  written by earlier versions.
- `BackendKind::ALL` and `BackendKind::from_id`, replacing the hand-written
  46-arm id match in the Tauri layer. A test keeps the list exhaustive.
- **Hold a Windows update by its KB number.** Its native id has to be
  `<guid>.<revision>` — that is what the Update Agent accepts, and pinning the
  exact revision is required by the backend contract — but nobody holds an
  update by GUID. `PackageId` now carries an optional alias that the policy
  engine also matches, so `odysync hold KB5101650` works. The alias is
  deliberately excluded from equality and hashing: `PackageId` is a map key and
  correlates a scan result with its apply outcome, so a label must not change
  identity.
- **`odysync pause <backend> --days N` and `odysync resume <backend>`.** A
  deadline rather than an off switch — "off" gets set during one bad week and
  is still off a year later, which is how machines end up unpatched. An
  unparseable deadline in a hand-edited config is treated as *expired* rather
  than permanent, so a typo cannot silently stop security updates forever.
- An empty or whitespace-only pattern in `exclude` or `holds` now matches
  nothing. It previously compared equal to a package whose native id was
  empty, and silently skipping an update is the exact failure the policy engine
  exists to prevent.
- `odysync backends` now names **who** verifies each backend's payloads —
  winget, apt, the Windows Update Agent — instead of implying Odysync did.
  Odysync almost never holds an installer file: the package manager downloads
  and validates it inside its own process. AppImage is reported as *not
  verified*, with the reason.
- **Driver backup and rollback.** `odysync drivers backup | list |
  rollback --to <id> | prune --keep <n>` exports the Windows driver store per
  package, with a manifest, and can re-add a saved package later. Exporting
  works unelevated; restoring does not.
  - Nothing parses a `pnputil` label — its output is fully localised and the
    console code page mangles non-ASCII on the way out. The parser reads
    values: `oem<n>.inf` is a published name in every language.
  - Automatic backup before applying driver updates is **off by default**:
    `DriverStore\FileRepository` measured 4.7 GB here, so an automatic export
    at the default retention would spend over ten gigabytes of the user's disk.
    `odysync apply` instead names the most recent backup, or says plainly that
    there is none. `driver-backup-before-apply` opts in.
  - Restore is not a forced downgrade, and says so on every run: Windows ranks
    driver packages, so a newer one still in the store can keep winning.
- Dependabot for cargo, npm and GitHub Actions, grouped weekly.
- `npm audit --audit-level=moderate` in the GUI CI job. Rust dependencies were
  audited by `cargo-audit` and `cargo-deny`; the 116 npm packages were not
  audited at all.

### Security
- **The offline cache refused nothing.** `download_and_cache` accepted an
  arbitrary URL from the front-end, including plaintext `http://`, where an
  installer can be replaced in transit — and `expected_sha256` is optional, so
  often nothing would have caught the swap. It is now HTTPS-only, and other
  schemes are refused.
- The offline cache is now the first real call site of `odysync-verify`. A
  download is staged under a `.partial` name, its Authenticode signature is
  checked, and only then is it moved into place. An **invalid** signature
  deletes the file and fails the download; unsigned is allowed but recorded in
  the manifest as `CachedSignature::Unsigned` rather than passing silently.
- A malformed `expected_sha256` is rejected as a caller error instead of
  degrading into an ordinary "digest did not match".

### Fixed
- **No driver could ever be installed.** The driver backend set
  `available = Version::parse("{update_guid}.{revision}")`, which collapses to
  the GUID's first block and parses as `Version::Unknown`. The policy engine
  blocks unknown versions and `apply` refused them outright, so drivers were
  listed and never installable. Windows updates now carry an orderable
  `0` → revision pair instead.
- **Driver installs never downloaded and never accepted a EULA.** The install
  path went straight from `SetUpdates` to `Install`, which fails with
  `WU_E_NOT_DOWNLOADED` unless Windows had already cached the update.
- **A failed search discarded valid results.** `orcFailed` was treated as "no
  updates", but the Windows Update Agent returns that code alongside a
  populated collection when one source in the aggregate fails. On the machine
  this was found on, that meant throwing away 17 pending updates.
- **Windows Update appeared to require elevation, and did not.** The WUA
  backends activated the COM object with `CLSCTX_LOCAL_SERVER`, forcing
  out-of-process activation that an unelevated caller may not perform —
  `E_ACCESSDENIED`. With `CLSCTX_ALL` the search runs unelevated, so an
  ordinary user now sees pending security updates and the reason they cannot
  be applied yet, instead of an empty page.
- **`RunReport::reboot_required` was never set to `true`.** It had three
  display sites in the GUI, one in the CLI renderer, and no assignment
  anywhere. The runner now asks the OS through `platform::reboot_pending`,
  which covers every backend rather than only the one that installed.
- **The npm and VS Code backends never worked on Windows.** `CreateProcess`
  only appends `.exe` when searching `PATH`; npm ships as `npm.cmd` and the VS
  Code CLI as `code.cmd`, so both reported themselves unavailable on every
  Windows host. `proc::resolve_program` now walks `PATH` against `PATHEXT`
  without routing through a shell.
- Duplicate Windows Update offerings — the same Defender signature listed once
  per servicing channel — are deduplicated on identity.
- The GUI lockfile version, which had drifted to `2.0.0-alpha.1` against a
  `2.1.0` `package.json`.

### Removed
- The v1 Python implementation (`legacy/`, 23 files). The Rust CLI has had
  feature parity since Phase 2, and this was the last open item on the
  rewrite roadmap. The Python tool remains available at the `v1.3.0` tag.

## [2.1.0]

### Added
- **Security page** — posture and indicator-of-compromise audit across five
  sections (Defender, persistence, integrity, network, hardening). Drives
  Microsoft Defender for malware scanning rather than implementing an engine;
  each section fails independently so a failure is never mistaken for a clean
  result. Remediation quarantines instead of deleting, refuses paths under
  `C:\Windows` or `Program Files`, and requires explicit confirmation.
- **Hardware Updates page** — drivers, firmware and vendor tools, grouped, with
  a separate confirmation step for firmware and a forced restore point.
- Start with Windows, optionally minimised to the tray (`--minimized`).
- `Backend::list_installed()` — a real inventory call, implemented for winget,
  chocolatey, scoop, pip, npm, cargo, dotnet and VS Code.
- Log viewer auto-scroll; error boundaries and frontend crash reporting into
  `odysync.log`.

### Fixed
- **Saving settings reset the entire config**, destroying `policy.holds` and
  `policy.exclude`: `Config` serializes kebab-case, the GUI posted snake_case,
  and `#[serde(default)]` with no `deny_unknown_fields` read that as "all
  fields absent". A held package silently became updatable again.
- **Arbitrary file deletion** via `remove_offline_entry`: an unvalidated
  `filename` from `manifest.json` was joined to the cache directory, and an
  absolute path there discards the base entirely.
- **PowerShell command injection** in `toggle_startup_program`, which
  interpolated registry-sourced strings unescaped; the same function referenced
  an undefined `$enable`, so entries could be disabled but never re-enabled.
- Every page refetched on navigation, losing state and re-scanning in a loop.
- `restore_backup` used the list index as the restore-point sequence number.
- Update history was never written (`Runner::with_history` had no call sites)
  and used a different config directory than everything else.
- "Installed Packages" listed only *upgradable* packages.
- Backend availability was re-probed (~36 process spawns) on every page load
  and always reported `true`.
- Failures reported as facts: a denied restore-point query as "none found", a
  disabled System Protection as the 24-hour throttle, unexpanded `%SystemRoot%`
  paths as deleted files, and an unparsed `{"value":[…]}` collection as
  "Defender absent or superseded by a third-party AV".
- `Remove-MpThreat -ThreatID` — no such parameter exists.

### Changed
- Severity policy: "unsigned", "outside `C:\Windows`" and "user-writable" are
  treated as context rather than signals, since per-user installs are how most
  software ships and self-built binaries are unsigned by definition. Only real
  indicators escalate. Handled Defender detections that never executed drop to
  informational; ones that *ran* keep full severity.
- Apply outcomes expose a stable status discriminant instead of `Debug` output.
- `Config::max_retries` is now actually used by the runner.

## [Unreleased] - v2.0.0

### Added
- Complete Rust rewrite of the Python toolchain
- `odysync-core` crate: policy engine, version algebra, planner, runner, config
- `odysync-verify` crate: installer digest and signature verification
- `odysync-backends` crate: winget, msstore, Windows drivers, homebrew, apt, flatpak
- `odysync-cli` crate: the `odysync` CLI (scan, apply, backends, hold, unhold, config, maintain, schedule, unschedule, diagnostics, daemon)
- `odysync-gui` crate: Tauri v2 + React + TypeScript + TailwindCSS desktop GUI
  - Updates tab: scan, select, apply with dry-run and restore point options
  - Maintenance tab: temp cleanup, recycle bin, system health, startup programs
  - Schedule tab: create/remove daily/weekly scheduled tasks
  - Settings tab: policy toggles, exclusions, backend status, config save
  - Dark/light mode with system-following default
- `odysync daemon` command for background scan/apply loops
- System tray icon with Show/Scan/Quit menu
- CI: cargo-audit, cargo-deny, CycloneDX SBOM generation
- Release workflow: cross-platform CLI builds with SHA-256 checksums, Tauri GUI NSIS installer

### Changed
- Windows driver updates now use the built-in Windows Update Agent COM API
- Version comparison uses proper semver ordering instead of string comparison
- Failed updates no longer fall back to reinstalling from scratch
- README rewritten for v2

### Fixed
- Lexical version comparison trap (`1.10` vs `1.9`)
- Unknown-version upgrades that could sidegrade or downgrade packages
- Reinstall-on-failure that wiped working package state
- Supply-chain hole from runtime-installed PowerShell module
- `is_elevated()` now uses `OpenProcessToken` + `GetTokenInformation`

### Security
- Policy engine refuses downgrades, same-version reinstalls, and pre-releases by default
- Store apps refused while elevated; driver updates refused without elevation

## [1.3.0] - 2025-10-20
### Added
- Visible progress animation during silent and interactive installs.
- Upgrade-scan cache with TTL (default 15 minutes), configurable via settings.
- Profiles export/import via CLI and Menu.
- Microsoft Store Library helper to open updates page.
- Log files for every run in `%LOCALAPPDATA%\Odysync\logs\`.

### Changed
- Faster, more resilient winget parsing with graceful timeouts and cache fallback.
- Settings file now includes defaults and cache TTL.

### Fixed
- Menu responsiveness while scanning; clearer feedback when winget is slow.

## [1.2.0] - 2025-10-20
### Added
- Run summaries and exportable reports (`--report json|txt`, `--out <path>`)
- Profiles and non-interactive updates (`--profile <name>`, `--yes`)
- Diagnostics pack (`--diagnostics`, `--diag-out <zip>`)
- Pending reboot detection with safety warning
- Scheduling via Windows Task Scheduler (`--schedule weekly|monthly`, `--time`, `--task-name`, `--unschedule`)
- EXE-first build flow and build script
- Modular package structure under `src/`

### Changed
- Smarter handling of Microsoft Store apps with context guidance
- Aggregated results for winget updates (updated, interactive, reinstalled, skipped, store-skipped, failed)
- Expanded README and troubleshooting

### Fixed
- Encoding issues by enforcing UTF-8 in PowerShell and console

### Notes
- No telemetry; privacy by default