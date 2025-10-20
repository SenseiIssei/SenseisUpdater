# Changelog

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