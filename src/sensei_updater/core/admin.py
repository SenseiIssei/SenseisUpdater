import ctypes, sys
from .console import Console

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def run_as_admin(argv=None) -> bool:
    """
    Relaunch the current Python with elevation (UAC). Returns True if the
    ShellExecute call was issued (i.e., elevation prompt shown).
    """
    if argv is None:
        argv = [sys.executable] + sys.argv
    try:
        params = " ".join(f'"{a}"' if " " in a else a for a in argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", argv[0], params, None, 1)
        return True
    except Exception:
        return False

def require_admin_or_msg(console: Console, action_label: str = "This action") -> bool:
    """
    Returns True if already elevated. If not, prints a friendly message and returns False.
    Callers can then early-return without crashing the UI.
    """
    if is_admin():
        return True
    console.err(f"✘ {action_label} requires Administrator.")
    console.info("→ Re-open Terminal/PowerShell as Administrator and try again.")
    return False