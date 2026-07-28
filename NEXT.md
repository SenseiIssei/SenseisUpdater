# What is left, and what is known

Written at the end of the `dev/iobit-parity` work, on a machine that is about
to be wiped of this checkout. Everything here is reconstructable from the
repository alone — no local state is assumed, because none survives.

`PLAN.md` records what was done and why. This file is the forward-looking half:
what remains, what was learned that a future session would otherwise have to
rediscover, and in what order it is worth doing.

---

## 0. Immediate: the branch is not merged

`dev/iobit-parity` is ahead of `main` by nine commits and has never been
merged. Nothing is lost — the branch is on the remote — but `main` does not yet
have the Windows Update backend, driver backup, cleanup, or any of the Phase F
work.

```sh
git checkout main
git merge --no-ff dev/iobit-parity
git push
```

Deliberately **not tagged**. Tagging `v2.2.0` triggers `release.yml`, which
publishes a public GitHub release. Two reasons to think before doing that:

1. Releases are unsigned (§1), so every user gets a SmartScreen warning.
2. Two code paths are still unverified (§2).

Neither is a blocker if the release is understood to be a pre-signing one. The
version numbers are already bumped to 2.2.0 across `Cargo.toml`,
`tauri.conf.json` and `apps/gui/package.json`.

**Old branches, once merged.** These are fully contained in `main` and safe to
delete:

```sh
git push origin --delete dev/rust-rewrite dev/updateMilestone2
```

These two are **not** safe to delete as-is:

| Branch | Unique commits | Why it needs care |
|---|---|---|
| `backup/pre-trailer-strip` | 4 | The safety net from a completed history rewrite. Its purpose is served, and the legacy Python tree it carries also exists at tag `v1.3.0`. Safe once you accept that. |
| `dev/ms3` | 3 | *"backup: work in progress before PC reset"*, plus a Python-era drivers-page UI and cycle/reports/schedule pages. **No tag contains these commits** — deleting the branch makes them unreachable. Tag it first (`git tag archive/ms3 origin/dev/ms3 && git push --tags`) and then the branch can go. |

---

## 1. Code signing — the one thing blocking everything else

Fully documented in [`docs/SIGNING.md`](docs/SIGNING.md): why it matters, the
certificate comparison, the exact repository variables and secrets, and how to
verify a signed artifact.

The CI side is **done and inert**. `release.yml` signs both the CLI binaries
and the NSIS installer, gated on a `SIGNING_ENABLED` repository variable. It
was built this way on purpose: the pipeline change does not have to be
remembered at the same moment the identity validation clears. Set the variable
and the secrets, and the next tag is signed.

Azure Trusted Signing, ~10 USD/month. The awkward requirement is that an
individual subscriber's identity must have existed for three years; if that
cannot be satisfied, an OV certificate is the fallback and early releases will
still warn.

**This gates automatic self-update, and the ordering is not negotiable.**
`self_update.rs` checks for a newer release and refuses to install it.
`ARCHITECTURE.md` criticises v1 for fetching a PowerShell module at runtime as
Administrator and trusting whatever answered; downloading an unsigned
executable and running it elevated is the same hole with our own name on it.
`UpdateCheck::is_installable` is the single place that decision lives, and the
test `odysync_refuses_to_install_its_own_updates_while_releases_are_unsigned`
is what will fail — deliberately — on the day signing lands. That failure is
the reminder.

---

## 2. Two paths that still have not been exercised

Everything else in this branch was verified against a real system. These two
were not, and the reason is worth recording so the next attempt does not
repeat it.

Both need **administrator rights**. Neither has anything to do with the
certificate — that conflation cost an afternoon.

### Windows Update install

The scan half is verified: it finds real pending updates on a real machine.
The install half is covered only by unit tests.

The elevated attempt failed with `0x8024001E`, and the cause is specific:
**UAC on that machine elevated into a different account** (`VISICON\jahoadm`)
than the interactive one (`VISICON\jaho`), and the Windows Update Agent will
not start its server outside the session it belongs to. The interactive user
*was* in Administrators, so this was policy, not permissions.

That is now explained in `explain_hresult` rather than surfacing as a hex
number, which is a genuine improvement that came out of the failure. But the
install path is still unproven.

**To verify:** an elevated session running as the *signed-in* account, on a
machine where UAC does not switch users — a non-domain machine is the easy
case. Then:

```sh
odysync scan --show-skipped          # confirm the WUA search works elevated
odysync apply --yes --only KB5101650 # one real update, scoped by KB number
```

Scoping by KB also exercises the `PackageId` alias matching in a real apply.
Expect a reboot prompt afterwards for a cumulative update.

### Driver restore

Backup, list and prune **are** verified elevated — and the restore run is what
found the `ERROR_NO_MORE_ITEMS` defect now fixed. What has not been seen is a
restore that actually installs a driver onto a device, because the test
deliberately used an already-current package.

**To verify:** back up a package, let Windows Update replace that driver with a
newer one, then restore and confirm `restored` (not `already_current`) comes
back non-empty. Note the documented limit: this is not a forced downgrade, so
if the newer package is still in the store Windows may keep preferring it, and
`already_current` is then the *correct* answer.

---

## 3. Carried over from PLAN.md, unchanged

- **GUI:** a Windows Update card exists; the driver-backup UI on the Hardware
  page does not. `drivers backup|list|rollback|prune` are CLI-only.
- **Startup impact score:** deliberately not built. Task Manager's rating comes
  from undocumented telemetry, and a number that looks like it but disagrees is
  worse than none. Offering *delay* as well as disable is still worthwhile and
  needs no score.
- **Large-file and duplicate reporting:** report-only and genuinely useful, but
  a full-disk hash walk could not be verified in the time available. Left open
  rather than shipped unverified.
- **Publisher allow-list:** dropped. With no installer on the apply path, its
  only possible site is the offline cache, and an allow-list of one is a
  configuration burden rather than a control. Revisit if a backend ever
  downloads its own payload.
- **macOS/Linux signing:** Developer ID plus notarisation for macOS (Gatekeeper
  refuses unnotarised apps outright, so this is required before a macOS GUI
  release). Signed repository packaging for Linux.

---

## 4. Things learned that are not obvious from the code

Recorded because each one cost real time and none of them are guessable.

**`pnputil` output is fully localised, and the console mangles it.** On a
German machine `Published Name` reads `Veröffentlichter Name`, with the umlaut
damaged by the code page. `driver_backup::parse_enum_drivers` therefore reads
*values*, never labels: an `oem<n>.inf` token is a published name in every
locale. Do not "improve" it by matching on field names.

**That parser had a bug unit tests could not catch.** It split records on
`"\n\n"`. `pnputil` is a Windows console program, so its blank line is
`\r\n\r\n` and the split never matched — the whole output collapsed into one
block and it returned **1 package on a machine with 215**. The tests passed
throughout, because they were written with `\n` and only ever tested their own
assumption. Every parser test now runs against both line endings, and one
asserts a record *count*, because the failure mode returns exactly one item no
matter how many exist. **Assert counts against ground truth, not shapes.**

**A full driver-store export is about 5 GB.** Measured:
`DriverStore\FileRepository` was 4.7 GB across 5 229 files, and a single
exported package was 22.5 MB × 215 packages. That measurement is why automatic
pre-apply backup is off by default — at the default retention it would spend
over ten gigabytes of the disk the tool is meant to be looking after, and
Windows already keeps a single-step rollback in Device Manager.

**The obvious way to measure the Recycle Bin is wrong.**
`Shell.Application.NameSpace(0xA).Items().Size` reported **1.1 MB** where the
truth was **881.7 MB**: `.Size` does not recurse into deleted folders, and it
missed the `D:` drive entirely. `SHQueryRecycleBinW` is authoritative. This is
also why `cleanup` does not walk `$Recycle.Bin` itself — that path is
per-user, permission-guarded, and exactly the shape the root-safety rule
refuses.

**Odysync almost never holds an installer file.** winget, apt, Homebrew and the
Update Agent each download, verify and execute the payload inside their own
process. This is why `odysync-verify` had no call sites for so long, and why
wiring it into the runner would have produced a hook that never fires. The one
real call site is the offline cache. `verification_of` exists to answer "who
checked this?" honestly instead of showing a tick that could be misread.

**Measure before trusting a number the tool prints.** Every figure in `PLAN.md`
was checked against an independent count. Two matched exactly, one did not —
and the one that did not was the *check* being wrong, not the tool. That is
only distinguishable because both were computed.
