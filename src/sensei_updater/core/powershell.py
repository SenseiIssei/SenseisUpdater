import os, tempfile, platform
from .process import Process

PS_PREFIX = r'''
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
'''

class PowerShell:
    def __init__(self, proc: Process):
        self.proc = proc
        self.exe = "powershell.exe" if platform.system() == "Windows" else "pwsh"

    def run(self, script: str) -> int:
        full = PS_PREFIX + "\n" + script
        f = None
        try:
            f = tempfile.NamedTemporaryFile(delete=False, suffix=".ps1", mode="w", encoding="utf-8")
            f.write(full)
            f.close()
            return self.proc.run_stream([self.exe, "-NoLogo","-NoProfile","-NonInteractive","-ExecutionPolicy","Bypass","-File", f.name])
        except Exception:
            return 1
        finally:
            try:
                if f and f.name and os.path.exists(f.name):
                    os.remove(f.name)
            except Exception:
                pass