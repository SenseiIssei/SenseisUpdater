# Odysync — Plan: full IObit-suite parity, done safely

Written 2026-07-27, against `main` @ `3adeeed`. Every claim below was checked
against the source, not against `README.md`.

The goal in one sentence: **Odysync should replace IObit Software Updater,
Driver Booster and Advanced SystemCare with one tool that never breaks a
working machine — and it must also install Windows' own updates.**

---

## 0. Where the code actually is today

Verified locally on this clone:

| Check | Result |
|---|---|
| `npm install` (apps/gui) | 116 packages, **0 vulnerabilities** |
| `npx tsc -b` | clean, exit 0 |
| `npx oxlint` | exit 0, 4 `only-export-components` warnings (cosmetic) |
| `cargo build --workspace --all-targets` | clean, 4m24s, zero warnings |
| `cargo fmt --all -- --check` | clean |
| `cargo clippy --workspace --all-targets` with `-D warnings` | clean |
| `cargo test --workspace --lib` | **440 passed, 0 failed** (README says 439) |
| CI | `rust.yml` runs fmt + clippy + tests + release build + GUI build on 3 OSes, plus `cargo-audit`, `cargo-deny`, CycloneDX SBOM |

The repo is **much further along than `README.md` and `ROADMAP.md` admit**.
README says "6 backends"; `all_backends()` registers **44 distinct backends**
(36 of them compiled in on Windows, 42 on Linux, 38 on macOS):

- Windows package managers: winget, Microsoft Store, Chocolatey, Scoop
- GPU: NVIDIA, AMD, Intel, Qualcomm
- OEM tools: Dell Command Update, HP Image Assistant, Lenovo System Update,
  MSI Center, ASUS Armoury, Gigabyte Control Center, Acer Care Center,
  Razer Synapse
- Firmware: Dell, HP, Lenovo; `fwupd` (Linux), Mac firmware
- Windows drivers via the Windows Update Agent COM API
- Language ecosystems: pip, cargo, npm, go, dotnet tool, VS Code extensions,
  JetBrains plugins, PowerShell modules, Windows optional features
- Unix: Homebrew, apt, dnf, pacman, zypper, snap, flatpak, nix, AppImage

The GUI has 17 pages (Dashboard, Updates, Drivers, Hardware, Maintenance,
Security, Startup, Schedule, Backup, Offline, Packages, Profiles, History,
Logs, Settings, About). The security module is ~6 000 lines across Defender,
persistence, integrity, network, posture and remediation.

**First action item: `README.md` and `ROADMAP.md` are stale and undersell the
project.** Fixing them is cheap and is part of Phase A.

Toolchain used: rustc 1.96.1, cargo 1.96.1, Node 24.14.1, npm 11.11.0.

**The tree is healthy.** Nothing in Phase A below is repair work; it is
verification and documentation catch-up.

---

## 1. Gap analysis against the three products the user named

| IObit product | Odysync today | Gap |
|---|---|---|
| **Software Updater** | 44 backends across 3 OSes, safety policy, holds/pins, offline cache, profiles | None worth naming. Odysync is already broader. |
| **Driver Booster** (hardware) | WUA driver search, 4 GPU vendors, 8 OEM tools, 3 firmware vendors, restore point before apply | **No driver backup, no driver rollback.** This is Driver Booster's single most valuable feature and the one that makes driver updating safe. |
| **Advanced SystemCare** | 4 maintenance actions (temp, recycle bin, DISM/SFC, startup viewer) + a real security audit IObit does not have | **Deep clean missing**: browser/privacy traces, WinSxS component cleanup, Delivery Optimization cache, `Windows.old`, large/duplicate files, disk optimize/TRIM, per-app startup impact. |
| **Windows Update itself** | Only `Type='Driver'` is searched (`windows_drivers.rs:137`) | **Windows quality, security and definition updates are not installed at all.** Largest functional gap. |

---

## 2. Defects found in the audit

These are things the code claims but does not do. They matter more than new
features, because they are trust claims.

1. **`odysync-verify` is never called.** The crate exists (188 + 175 lines,
   SHA-256 + Authenticode/codesign), is declared as a dependency in
   `crates/odysync-backends/Cargo.toml:16`, and has **zero call sites** in the
   whole workspace. `README.md` advertises "installer digest verification and
   signature checking" as a feature. Right now that is a dependency edge, not
   a behaviour. `offline.rs:447` does its own SHA-256 check, unrelated.

2. **No Windows OS updates.** `windows_drivers.rs` hard-codes
   `Type='Driver'` in both the scan and the install path. There is no
   `BackendKind::WindowsUpdate`.

3. **No driver backup or rollback.** `ROADMAP.md` is honest that rollback is
   "prevention, not undo" — but for drivers specifically, Windows gives us
   `pnputil /export-driver` and DriverStore rollback for free. Not using it is
   a choice we should reverse.

4. **Releases are unsigned.** No Authenticode, no notarisation, no self-update.
   Every install of Odysync shows a SmartScreen warning, which trains users to
   click through exactly the warning that protects them. `ROADMAP.md` §5 names
   this asymmetry and it is still open.

5. **No power/idle awareness** (`ROADMAP.md` §4) — a background scanner that
   runs on battery is a laptop problem.

6. **The driver install path never downloads and never accepts a EULA.**
   `install_driver_com` goes straight from `SetUpdates` to `Install`, with no
   `IUpdateDownloader` step and no `AcceptEula()`. `IUpdateInstaller::Install`
   requires `IsDownloaded == true` and fails with `WU_E_NOT_DOWNLOADED`
   (`0x80240034`) otherwise, so a driver install only succeeds when Windows
   happens to have cached the update already. Phase B's shared WUA wrapper
   fixes this for both backends at once.

7. **`RunReport::reboot_required` is never set to `true`.** The field is
   initialised `false` in `report.rs:36`, read in the CLI renderer and in three
   GUI components (`Dashboard.tsx:49`, `Drivers.tsx:184`, `Updates.tsx:238`) —
   and assigned nowhere. `install_driver_com` discards
   `IInstallationResult::RebootRequired()`. Three "a reboot is required"
   banners exist that can never appear.

8. **~~The npm and VS Code backends never worked on Windows.~~ Fixed.**
   `proc::build` called `Command::new("npm")`, and `CreateProcess` only ever
   appends `.exe` when searching `PATH`. npm ships as `npm.cmd` and VS Code's
   CLI as `code.cmd`, so both backends reported `is_available() == false` on
   every Windows machine — silently, because an unavailable backend is skipped
   rather than reported. `proc::resolve_program` now walks `PATH` against
   `PATHEXT` before spawning, without routing through a shell. Verified on this
   host: `odysync backends` went from 9 detected to 11, gaining `npm` and
   `vscode-extension`.

---

## 3. The plan

Six phases. Each is independently shippable and does not require the next one.

### Phase A — Trust the baseline (½ day)

Nothing new is built until the existing thing is proven.

- [x] `cargo fmt --check`, `cargo clippy --workspace --all-targets -- -D warnings`,
      `cargo test --workspace --lib` — all green locally, matching CI.
- [x] `cargo build --release -p odysync-cli` and a real smoke test.
      2.31 MB binary; `odysync backends` detects 11 on this host;
      `odysync scan` returned **50 real updates** (37 winget, plus pip).
- [x] Fixed the `PATHEXT` defect above; 3 regression tests added
      (`odysync-core` went from 75 to 78 tests, 443 in the workspace).
- [ ] `npx tauri build`, install the NSIS output, click every one of the 17
      pages, note anything that errors or hangs.
- [ ] Rewrite the stale parts of `README.md` (backend count, feature list) and
      `ROADMAP.md` (phases marked open that are done).
- [ ] *(optional, low value)* The 4 oxlint `only-export-components` warnings
      are a Fast-Refresh nicety, not a defect — `oxlint` exits 0. Worth doing
      only when `ui.tsx`/`store.tsx` are being touched anyway.

**Exit:** we know exactly what works, from evidence rather than documentation.

### Phase B — Windows Update (2–3 days) — *the headline gap*

New `BackendKind::WindowsUpdate`, next to `WindowsDrivers`, sharing one WUA
COM wrapper.

- [ ] Extract the COM plumbing from `windows_drivers.rs` into
      `windows_update/session.rs` behind a small trait, so both backends use
      it and so the search/install logic becomes unit-testable with a fake.
      **This is also where defects 6 and 7 get fixed**, for both backends at
      once: an `IUpdateDownloader` pass before `Install`, `AcceptEula()` on
      confirmed updates, and `IInstallationResult::RebootRequired()` wired
      through to `RunReport::reboot_required`.
- [ ] Search `IsInstalled=0 AND Type='Software'`, then classify each update by
      its categories: **Security**, **Critical**, **Definition** (Defender),
      **Quality/Cumulative**, **Feature upgrade**, **Optional/Preview**.
- [ ] Policy per class, in `odysync-core::policy` where every other safety rule
      lives:
      - Security + Critical: eligible by default.
      - Definition updates: eligible, fast path, no restore point (they are
        replaced hourly; a restore point per definition is absurd).
      - Quality/Cumulative: eligible, restore point first.
      - **Feature upgrades: opt-in only.** Never in an unattended run.
      - Preview/Optional: refused by default.
- [ ] EULA handling: `AcceptEula()` only for updates the user confirmed.
- [ ] Reboot: propagate `RunReport::reboot_required`, detect an already-pending
      reboot (`CBS\RebootPending`, `WindowsUpdate\Auto Update\RebootRequired`,
      `PendingFileRenameOperations`) and refuse to stack a second batch on top
      of one.
- [ ] Deferral, like Windows itself: hold a single KB, or pause all Windows
      updates for N days. Reuses the existing hold/pin config syntax
      (`windows-update:KB5034123`).
- [ ] Elevation: reuse the existing model. WUA install needs admin; the backend
      already reports `is_available() == false` unelevated, which is the right
      shape — carry it over.
- [ ] GUI: Windows Update gets its own card on the Updates page with the class
      breakdown, plus a "restart now / restart later" affordance.

**Exit:** `odysync scan` lists pending Windows security updates; `odysync apply`
installs them; reboot state is reported honestly.

**Risk:** WUA is a COM API with real failure modes (WSUS-managed machines,
policy-blocked updates, `0x80240438`). Each error path must produce a message
the user can act on, not a HRESULT.

### Phase C — Make the safety claims true (1–2 days)

- [ ] Wire `odysync-verify` into the apply path in `odysync-core::runner`, so
      **no backend can opt out**: any backend that hands us a downloaded
      installer path gets its digest and Authenticode signature checked before
      execution. Backends that never touch a file (winget, apt) pass through
      explicitly and say so in the report.
- [ ] Publisher allow-list: an installer signed by an unexpected publisher is
      refused, not warned about.
- [ ] Where verification genuinely cannot happen (winget hides its manifest
      hashes — `ROADMAP.md` known gap 2), the report must say
      "verified by winget, not by us" rather than showing a green tick.
- [ ] Add `npm audit --audit-level=moderate` to the `gui` CI job. Rust deps are
      audited; the 116 npm packages are not.
- [ ] Enable Dependabot or Renovate for both `Cargo.toml` and `package.json`.

**Exit:** every green "verified" in the UI corresponds to a check that ran.

### Phase D — Driver safety: backup and rollback (2 days)

This is what makes hardware updates defensible.

- [ ] Before any driver install: `pnputil /export-driver *` into
      `%LOCALAPPDATA%\Odysync\driver-backup\<timestamp>\`, with a manifest.
- [ ] `odysync drivers rollback --to <timestamp>` and a GUI button on the
      Hardware page, using DriverStore restore / `pnputil /add-driver /install`.
- [ ] Keep the forced restore point for firmware — firmware is the one thing
      that genuinely cannot be undone, and it should stay behind its own
      confirmation step (it already is).
- [ ] Retention policy: keep the last N backups, prune the rest.

**Exit:** a bad GPU driver is one click from being undone without safe mode.

### Phase E — Advanced SystemCare parity, minus the snake oil (3–4 days)

Every cleaner here follows the same contract: **scan first, show sizes,
delete only what the user ticked, never touch anything outside a known list.**

- [ ] Junk scanner with categories and byte counts, dry-run by default:
      - Windows Update cleanup — `DISM /StartComponentCleanup` (WinSxS)
      - Delivery Optimization cache
      - `Windows.old` (with a loud warning: this removes rollback to the
        previous Windows build)
      - Thumbnail/icon caches, error reports, memory dumps, prefetch
      - Per-user temp beyond `%TEMP%` (already covered)
- [ ] Browser traces (Chrome, Edge, Firefox): cache and history, **per profile,
      explicit tick per item, refused while the browser is running**. Cookies
      and saved passwords are never offered.
- [ ] Large files and duplicates: report-only, sorted by size, with an "open in
      Explorer" action. Odysync does not delete a user's own documents.
- [ ] Disk optimisation: `Optimize-Volume` — TRIM on SSD, defrag on HDD,
      detected per volume, never defrag an SSD.
- [ ] Startup impact: measure real boot delay per entry
      (`Explorer\StartupApproved` + task manager's impact data) and offer
      **delay** as well as disable — disabling an updater is how machines end
      up out of date.

**Exit:** the Maintenance page reports a credible reclaimable-space figure and
every action is reversible or clearly labelled as not.

### Phase F — Ship it properly (1 day of work, weeks of lead time)

- [ ] **Code signing.** Azure Trusted Signing is ~10 USD/month and the only
      practical route for an individual publisher; the alternative is an EV
      certificate at 300–500 USD/year. Without it, SmartScreen flags every
      release. Start this first — validation takes days, not minutes.
- [ ] Sign the NSIS installer and both binaries in `release.yml`.
- [ ] Self-update that verifies its own signature before applying
      (Tauri updater plugin + a signed `latest.json`).
- [ ] Publish a winget manifest for Odysync itself. A tool that updates
      software should be installable with `winget install Odysync`.
- [ ] Idle/AC awareness in the daemon; measure idle RSS against the 15 MB
      target in `ROADMAP.md` rather than assuming it.
- [ ] Tag `v2.2.0`, write the release notes.

---

## 4. What I recommend *not* building

Stated plainly, because these are the parts of Advanced SystemCare that sell
copies and damage machines.

1. **A registry cleaner that writes.** Measured benefit on a modern Windows
   install is indistinguishable from zero; the failure mode is an unbootable
   system. **Decided: report-only.** Orphaned entries are found and shown;
   Odysync never edits the registry to "clean" it.
2. **"RAM boost" / memory optimisers.** Freeing working sets forces the pages
   straight back off disk. It makes the machine slower and the graph prettier.
3. **Network "tuning"** via TCP registry tweaks. Windows autotunes; these
   settings are cargo-cult. A diagnostic report (DNS latency, packet loss,
   driver version) is genuinely useful — the tweaks are not.
4. **Automatic feature upgrades.** A cumulative update is routine; a Windows
   version upgrade is not something a background daemon should start.

---

## 5. Order and effort

| Phase | Effort | Why this order |
|---|---|---|
| A — verify baseline | ½ day | Never build on unverified ground |
| F₀ — start signing procurement | 1 h | Weeks of external lead time; start it on day one |
| B — Windows Update | 2–3 d | The named gap, and the highest user value |
| C — make verify real | 1–2 d | Trust claims outrank new features |
| D — driver backup/rollback | 2 d | Makes Phase B's driver half safe |
| E — deep clean | 3–4 d | Largest surface, lowest risk if the contract in §E holds |
| F — release | 1 d + lead time | Signed, self-updating, winget-installable |

Total: roughly two working weeks of focused effort, plus signing lead time.
