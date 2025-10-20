import subprocess
from .colors import MAGENTA, DIM, RESET, GRAY

class Process:
    def __init__(self, debug: bool=False, dry_run: bool=False):
        self.debug = debug
        self.dry_run = dry_run

    def run_stream(self, cmd):
        if self.debug: print(f"{MAGENTA}{DIM}>>> {' '.join(map(str, cmd))}{RESET}")
        if self.dry_run:
            print(f"{GRAY}[dry-run]{RESET} {' '.join(map(str, cmd))}")
            return 0
        try:
            p = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", shell=False
            )
            assert p.stdout is not None
            for line in p.stdout:
                if line.strip().startswith("VERBOSE:"):
                    print(f"{GRAY}{line.rstrip()}{RESET}")
                else:
                    print(line, end="")
            return p.wait()
        except KeyboardInterrupt:
            try: p.terminate()
            except Exception: pass
            return 1

    def run_capture(self, cmd):
        if self.debug: print(f"{MAGENTA}{DIM}>>> {' '.join(map(str, cmd))}{RESET}")
        if self.dry_run: return 0, ""
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", shell=False)
        return r.returncode, r.stdout