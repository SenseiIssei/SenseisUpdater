from ..core.process import Process
from ..core.console import Console
import json


class SystemService:
    def __init__(self, console: Console):
        self.console = console
        self.proc = Process(debug=console.debug, dry_run=console.dry_run)

    def has_pending_reboot(self) -> bool:
        rc, out = self.proc.run_capture([
            "powershell", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
            "(Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update\\RebootRequired' -ErrorAction SilentlyContinue) -ne $null"
        ])
        s = (out or "").strip().lower()
        return s == "true"

    def cleanup_temp(self):
        ps = r'''
$ErrorActionPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$path = $env:TEMP
if (-not (Test-Path $path)) { "{}" | ConvertFrom-Json | ConvertTo-Json -Compress; exit 0 }
$files = Get-ChildItem -LiteralPath $path -Recurse -Force -File -ErrorAction SilentlyContinue
$dirs  = Get-ChildItem -LiteralPath $path -Recurse -Force -Directory -ErrorAction SilentlyContinue
$bytes = ($files | Measure-Object -Property Length -Sum).Sum
$fc = @($files).Count
$dc = @($dirs).Count
Remove-Item -LiteralPath (Join-Path $path '*') -Recurse -Force -ErrorAction SilentlyContinue
@{ files=$fc; dirs=$dc; bytes=$bytes } | ConvertTo-Json -Compress
'''
        rc, out = self.proc.run_capture([
            "powershell", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
            "-Command", ps
        ])
        try:
            return json.loads(out) if out else {"files": 0, "dirs": 0, "bytes": 0}
        except Exception:
            return {"files": 0, "dirs": 0, "bytes": 0}

    def empty_recycle_bin(self):
        ps = r'''
$ErrorActionPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$shell = New-Object -ComObject Shell.Application
$rb = $shell.NameSpace(0xA)
$items = @($rb.Items())
$count = $items.Count
Clear-RecycleBin -Force -ErrorAction SilentlyContinue | Out-Null
@{ items=$count } | ConvertTo-Json -Compress
'''
        rc, out = self.proc.run_capture([
            "powershell", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
            "-Command", ps
        ])
        try:
            return json.loads(out) if out else {"items": 0}
        except Exception:
            return {"items": 0}

    def dism_sfc(self):
        def _run(cmd, timeout_s):
            rc, out, to = self.proc.run_capture_timeout(cmd, timeout_s)
            return rc, out or "", bool(to)

        scan_cmd = ["dism", "/online", "/cleanup-image", "/scanhealth"]
        rest_cmd = ["dism", "/online", "/cleanup-image", "/restorehealth"]
        sfc_cmd  = ["sfc", "/scannow"]

        rc1, out1, to1 = _run(scan_cmd, 1800)
        rc2, out2, to2 = _run(rest_cmd, 3600)
        rc3, out3, to3 = _run(sfc_cmd, 3600)

        def _state_scan(s):
            t = s.lower()
            if "no component store corruption detected" in t:
                return "OK"
            if "component store is repairable" in t or "corruption detected" in t:
                return "CorruptionDetected"
            if "timed out" in t:
                return "Timeout"
            return "Unknown"

        def _state_restore(s, rc):
            t = s.lower()
            if "the restore operation completed successfully" in t or "the operation completed successfully" in t or rc == 0:
                return "OK"
            if "failed" in t or "error" in t:
                return "Failed"
            return "Unknown"

        def _state_sfc(s):
            t = s.lower()
            if "did not find any integrity violations" in t:
                return "NoIntegrityViolations"
            if "found corrupt files and successfully repaired them" in t:
                return "Repaired"
            if "could not perform the requested operation" in t:
                return "Failed"
            return "Unknown"

        result = {
            "scanhealth": "Timeout" if to1 else _state_scan(out1),
            "restorehealth": "Timeout" if to2 else _state_restore(out2, rc2),
            "sfc": "Timeout" if to3 else _state_sfc(out3)
        }
        return result

    def show_startup(self):
        self.proc.run_capture([
            "powershell", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
            "Get-CimInstance Win32_StartupCommand | Select-Object Name,Command | Format-Table -AutoSize"
        ])

    def open_store_library(self):
        try:
            rc = self.proc.run_capture(["cmd", "/c", "start", "ms-windows-store://downloadsandupdates"])[0]
            return rc == 0
        except Exception:
            return False

    def ensure_app_installer(self):
        rc, _ = self.proc.run_capture(["winget", "--version"])
        if rc == 0:
            return True
        self.proc.run_capture(["cmd", "/c", "start", "ms-windows-store://pdp/?productid=9NBLGGH4NNS1"])
        return False