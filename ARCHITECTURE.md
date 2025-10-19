
---

## ARCHITECTURE.md

```markdown
# Architecture

## Overview

The application is a single Python module exposing one class, `SenseisUpdater`, which encapsulates all actions and UI. It runs in **user** or **admin** context and checks privileges per action.

Key goals:
- Safety first (restore point, guarded admin operations, best-effort temp cleanup)
- Robustness to localized `winget` output (generic table parser + JSON path)
- Smooth UX (ANSI colors, UTF-8 console, short commands in the selector)
- No background services; all actions are explicit

## Main modules

- `src/sensei_updater/app.py`  
  Contains:
  - `SenseisUpdater` with:
    - Admin detection and guarded actions
    - UTF-8 + ANSI console enabling
    - PowerShell runner enforcing UTF-8
    - Driver update flow (PSWindowsUpdate; supports new/legacy commands)
    - App update selector (parses `winget` `upgrade`/`list` output; falls back gracefully)
    - DISM/SFC and cleanup routines
  - `main()` which wires flags and launches the interactive menu

- `src/sensei_updater/__main__.py`  
  Console entry point so `python -m sensei_updater` works.

- `pyproject.toml`  
  Provides a `console_scripts` entry point `sensei-updater` for `pip install -e .`.

## Key design decisions

- **Per-action admin checks**: instead of forcing elevation at startup, only admin-required operations (drivers, cleanup, DISM/SFC, restore point) are blocked when not elevated.
- **Winget parsing**: first try `--output json`; fallback to generic table parsing tolerant of localized headers. We validate IDs and prevent version strings from being mistaken for IDs.
- **Store vs non-Store**: Microsoft Store apps must be updated in user context; the tool detects this and instructs accordingly. For non-Store failures, it retries interactive, then falls back to reinstall.
- **Encoding resilience**: PowerShell scripts set `OutputEncoding` to UTF-8; Python subprocess reads with `encoding="utf-8", errors="replace"`.

## Extensibility

- Add new menu items by extending `interactive_menu()` and implementing a method.
- Add new profiles/filters in the selector by editing `selector_loop()`.
- To support other package managers, add additional discovery/update methods beside `winget_*`.