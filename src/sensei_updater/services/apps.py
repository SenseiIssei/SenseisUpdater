import re, json
from ..core.process import Process
from ..core.colors import *
from ..core.console import Console

def looks_like_version(s:str) -> bool:
    return bool(re.fullmatch(r"[0-9]+(\.[0-9A-Za-z\-+]+)+", s or ""))

def looks_like_id(s:str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-\._]+[A-Za-z0-9]", s or "")) and (" " not in s) and ("." in s)

class AppService:
    def __init__(self, console: Console, cfg):
        self.console = console
        self.proc = Process(debug=console.debug, dry_run=console.dry_run)
        self.cfg = cfg

    def _parse_table(self, text: str):
        lines = [ln.rstrip() for ln in (text or "").splitlines()]
        rows = []
        for s in lines:
            t = s.strip()
            if not t: continue
            l = t.lower()
            if l.startswith("found ") or l.startswith("the following") or l.startswith("no "): continue
            cols = re.split(r"\s{2,}", t)
            if len(cols) < 2: continue
            name = cols[0]
            if len(cols) >= 2 and looks_like_id(cols[1]) and not looks_like_version(cols[1]):
                pid = cols[1]
                version  = cols[2] if len(cols) >= 3 else ""
                available= cols[3] if len(cols) >= 4 else ""
                source   = cols[4] if len(cols) >= 5 else ""
            elif len(cols) >= 3 and looks_like_version(cols[1]) and looks_like_id(cols[2]):
                pid = cols[2]
                version  = cols[1]
                available= cols[3] if len(cols) >= 4 else ""
                source   = cols[4] if len(cols) >= 5 else ""
            else:
                pid = version = available = source = ""
                for c in cols[1:]:
                    if not pid and looks_like_id(c) and not looks_like_version(c): pid = c
                    elif not version and looks_like_version(c): version = c
                    elif not available and looks_like_version(c): available = c
                    elif not source and c.lower() in ("winget","msstore","store","msi","exe","msix"): source = c
            if not pid: continue
            rows.append({"Name":name,"Id":pid,"Version":version,"Available":available,"Source":source})
        dedup = {}
        for r in rows: dedup[r["Id"]] = r
        return list(dedup.values())

    def _json_supported(self) -> bool:
        rc,_ = self.proc.run_capture(["winget","--version"])
        if rc != 0: return False
        rc,out = self.proc.run_capture(["winget","upgrade","--output","json"])
        s=(out or "").strip()
        return rc==0 and (s.startswith("{") or s.startswith("["))

    def list_upgrades(self):
        if self._json_supported():
            rc,out = self.proc.run_capture(["winget","upgrade","--output","json"])
            if rc==0 and out:
                try:
                    data = json.loads(out)
                    def mapit(p):
                        return {
                            "Id": p.get("PackageIdentifier") or p.get("Id") or "",
                            "Name": p.get("PackageName") or p.get("Name") or "",
                            "Version": p.get("InstalledVersion") or p.get("Version") or "",
                            "Available": p.get("AvailableVersion") or p.get("Available") or "",
                            "Source": p.get("Source") or "",
                        }
                    arr = data.get("InstalledPackages", []) if isinstance(data, dict) else data
                    return [x for x in map(mapit, arr) if x["Id"]]
                except json.JSONDecodeError:
                    pass
        for cmd in (["winget","upgrade"],
                    ["winget","upgrade","--include-unknown"],
                    ["winget","upgrade","--source","winget"],
                    ["winget","upgrade","--source","msstore"]):
            rc,out = self.proc.run_capture(cmd)
            if rc==0 and out:
                rows = self._parse_table(out)
                if rows: return rows
        return []

    def list_installed(self):
        for cmd in (["winget","list"],
                    ["winget","list","--source","winget"],
                    ["winget","list","--source","msstore"]):
            rc,out = self.proc.run_capture(cmd)
            if rc==0 and out:
                rows = [r for r in self._parse_table(out) if looks_like_id(r.get("Id",""))]
                if rows: return rows
        return []

    # RETURN results dict for RunReport
    def update_ids(self, ids: list[str]):
        results = {
            "updated": [], "interactive": [], "reinstalled": [],
            "skipped": [], "store_skipped": [], "failed": []
        }
        self.console.header("Installing selected app updates (winget)")
        id_to_source = {}
        rc,out = self.proc.run_capture(["winget","upgrade"])
        if rc==0 and out:
            for r in self._parse_table(out):
                id_to_source[r["Id"]] = (r.get("Source","") or "").lower()

        user_ctx = not self.console.is_admin()

        for pid in ids:
            if not looks_like_id(pid) or looks_like_version(pid):
                self.console.warn(f"Skipping invalid Id (looks like a version or malformed): {pid}")
                results["skipped"].append(pid)
                continue

            src = id_to_source.get(pid,"")
            cmd = ["winget","upgrade","--id",pid,"--accept-package-agreements","--accept-source-agreements"]
            if src in ("msstore","store"):
                if not user_ctx:
                    self.console.warn(f"{pid} is a Microsoft Store app. Run in a NON-admin terminal and retry.")
                    results["store_skipped"].append(pid)
                    continue
                cmd += ["--source","msstore"]

            cmd_silent = cmd + ["--silent"]
            self.console.info(f"Updating {pid} ...")
            rc = self.proc.run_stream(cmd_silent)
            if rc == 0:
                self.console.ok(f"Updated (or already current): {pid}")
                results["updated"].append(pid)
                continue

            if src in ("msstore","store"):
                self.console.warn(f"{pid}: Store upgrade failed. Open Microsoft Store → Library → Get updates.")
                results["failed"].append(pid)
                continue

            # retry interactive
            self.console.info(f"{pid}: retrying interactive…")
            cmd_interactive = [c for c in cmd if c!="--silent"] + ["--interactive"]
            rc2 = self.proc.run_stream(cmd_interactive)
            if rc2 == 0:
                self.console.ok(f"Updated interactively: {pid}")
                results["interactive"].append(pid)
            else:
                # reinstall fallback
                self.console.info(f"{pid}: trying reinstall…")
                rc3 = self.proc.run_stream(["winget","install","--id",pid,"--accept-package-agreements","--accept-source-agreements","--silent"])
                if rc3 == 0:
                    self.console.ok(f"Reinstalled: {pid}")
                    results["reinstalled"].append(pid)
                else:
                    self.console.warn(f"Failed or not applicable: {pid}")
                    results["failed"].append(pid)

        return results