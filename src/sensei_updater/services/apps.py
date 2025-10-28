import re, json, time, shutil, threading
from typing import List, Dict, Any, Tuple
from ..core.process import Process
from ..core.console import Console
from ..data.paths import CONFIG_DIR

def looks_like_version(s: str) -> bool:
    return bool(re.fullmatch(r"[0-9]+(\.[0-9A-Za-z\-+]+)+", s or ""))

def looks_like_id(s: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-\._]+[A-Za-z0-9]", s or "")) and (" " not in s) and ("." in s)

class AppService:
    def __init__(self, console: Console, cfg):
        self.console = console
        self.proc = Process(debug=console.debug, dry_run=console.dry_run)
        self.cfg = cfg
        self.cache_path = CONFIG_DIR / "last-upgrades.json"
        self.cache_ttl_min = int((self.cfg.get_defaults() or {}).get("cache_ttl_minutes", 10))
        self._silent_cache: Dict[str, bool] = {}

    def _has(self, exe: str) -> bool:
        return shutil.which(exe) is not None

    def check_environment(self):
        if not self._has("winget") and not self._has("choco") and not self._has("scoop"):
            raise RuntimeError("No package manager found (winget/choco/scoop)")
        return True

    def _cache_write(self, rows: List[Dict[str, Any]]) -> None:
        try:
            self.cache_path.write_text(json.dumps({"ts": time.time(), "rows": rows}, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _cache_read(self) -> List[Dict[str, Any]]:
        try:
            if self.cache_path.exists():
                j = json.loads(self.cache_path.read_text(encoding="utf-8"))
                ts = float(j.get("ts") or 0)
                if ts and (time.time() - ts) <= self.cache_ttl_min * 60:
                    rows = j.get("rows") or []
                    if isinstance(rows, list):
                        return rows
        except Exception:
            pass
        return []

    def _winget_json(self, args: List[str], timeout_s: int) -> Any:
        base = ["winget"] + args + ["--accept-source-agreements","--accept-package-agreements","--disable-interactivity","--output","json"]
        rc, out, to = self.proc.run_capture_timeout(base, timeout_s)
        if to or not out:
            return []
        s = (out or "").strip()
        if not s or (not s.startswith("{") and not s.startswith("[")):
            return []
        try:
            return json.loads(s)
        except Exception:
            return []

    def _parse_table(self, text: str) -> List[Dict[str, Any]]:
        lines = [ln.rstrip() for ln in (text or "").splitlines()]
        rows: List[Dict[str, Any]] = []
        for s in lines:
            t = s.strip()
            if not t:
                continue
            low = t.lower()
            if low.startswith("name ") or low.startswith("id ") or low.startswith("found ") or low.startswith("the following") or low.startswith("keine ") or low.startswith("no "):
                continue
            cols = re.split(r"\s{2,}", t)
            if len(cols) < 2:
                continue
            name = cols[0]
            rest = cols[1:]
            pid, versions, source = "", [], ""
            for c in rest:
                if not pid and looks_like_id(c):
                    pid = c
                    continue
                if looks_like_version(c):
                    versions.append(c)
                    continue
                cl = c.lower()
                if not source and cl in ("winget","msstore","store"):
                    source = c
            installed = versions[0] if len(versions) >= 1 else ""
            available = versions[1] if len(versions) >= 2 else ""
            if not pid:
                continue
            rows.append({"Name": name, "Id": pid, "Version": installed, "Available": available, "Source": source or "winget"})
        dedup: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            dedup[r["Id"]] = r
        return list(dedup.values())

    def _supports_silent(self, pid: str) -> bool:
        if pid in self._silent_cache:
            return self._silent_cache[pid]
        info = self._winget_json(["show","--id",pid,"--source","winget"], 25)
        ok = False
        try:
            items = [info] if isinstance(info, dict) else (info if isinstance(info, list) else [])
            installers = []
            for it in items:
                installers += (it.get("Installers") or it.get("InstallersList") or [])
            for inst in installers:
                switches = inst.get("InstallerSwitches") or {}
                if switches.get("Silent") or switches.get("SilentWithProgress"):
                    ok = True
                    break
                itype = (inst.get("InstallerType") or "").lower()
                if itype in ("msix","appx"):
                    ok = True
                    break
        except Exception:
            ok = False
        self._silent_cache[pid] = ok
        return ok

    def _filter_updatable(self, rows: List[Dict[str, Any]], skip_store: bool=True) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []
        for r in rows:
            pid = r.get("Id","")
            if not looks_like_id(pid):
                continue
            src = (r.get("Source") or "").lower()
            if skip_store and src in ("msstore","store"):
                continue
            available = r.get("Available") or ""
            installed = r.get("Version") or ""
            if not available or available == installed:
                continue
            if src in ("","winget") and not self._supports_silent(pid):
                continue
            filtered.append(r)
        return filtered

    def _run_winget_sources(self) -> None:
        if not self._has("winget"):
            return
        self.proc.run_capture_timeout(["winget","source","update"], 15)
        self.proc.run_capture_timeout(["winget","settings","export","-"], 10)

    def _list_winget_fast(self, timeout_upgrade: int) -> List[Dict[str, Any]]:
        if not self._has("winget"):
            return []
        data = self._winget_json(["upgrade","--include-unknown"], timeout_upgrade)
        rows: List[Dict[str, Any]] = []
        arr = data.get("InstalledPackages", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        for p in arr or []:
            pid = p.get("PackageIdentifier") or p.get("Id") or ""
            if not looks_like_id(pid):
                continue
            rows.append({
                "Id": pid,
                "Name": p.get("PackageName") or p.get("Name") or pid,
                "Version": p.get("InstalledVersion") or p.get("Version") or "",
                "Available": p.get("AvailableVersion") or p.get("Available") or "",
                "Source": (p.get("Source") or "winget"),
                "Interactive": p.get("IsInteractive", False),
            })
        if rows:
            return rows
        rc, out, to = self.proc.run_capture_timeout(["winget","upgrade","--source","winget"], min(45, timeout_upgrade))
        if rc == 0 and not to and out:
            return self._parse_table(out)
        return []

    def _list_choco(self, timeout_s: int) -> List[Dict[str, Any]]:
        if not self._has("choco"):
            return []
        rc, out, to = self.proc.run_capture_timeout(["choco","outdated","-r"], timeout_s)
        if to or rc not in (0, 2):
            out = out or ""
        rows = []
        for line in (out or "").splitlines():
            parts = [x.strip() for x in line.split("|")]
            if len(parts) >= 3 and looks_like_id(parts[0]):
                rows.append({"Id": parts[0], "Name": parts[0], "Version": parts[1], "Available": parts[2], "Source": "choco"})
        return rows

    def _list_scoop(self, timeout_s: int) -> List[Dict[str, Any]]:
        if not self._has("scoop"):
            return []
        rc, out, to = self.proc.run_capture_timeout(["scoop","status","-r"], timeout_s)
        rows = []
        for line in (out or "").splitlines():
            t = line.strip()
            if not t or "is up to date" in t.lower():
                continue
            if "->" in t:
                name = t.split()[0]
                ver = t.split("->")[-1].strip()
                if name:
                    rows.append({"Id": name, "Name": name, "Version": "", "Available": ver, "Source": "scoop"})
        return rows

    def list_upgrades_all(self, force_refresh: bool=False, skip_store: bool=True, scan_timeout: int=120) -> List[Dict[str, Any]]:
        if not force_refresh:
            cached = self._cache_read()
            if cached:
                return cached
        self._run_winget_sources()
        per = max(20, min(180, scan_timeout))
        winget_rows: List[Dict[str, Any]] = []
        choco_rows: List[Dict[str, Any]] = []
        scoop_rows: List[Dict[str, Any]] = []
        threads: List[Tuple[threading.Thread, List[Dict[str, Any]]]] = []

        def t_winget(dst: List[Dict[str, Any]]):
            dst.extend(self._filter_updatable(self._list_winget_fast(min(per, 90)), skip_store=skip_store))

        def t_choco(dst: List[Dict[str, Any]]):
            dst.extend(self._list_choco(min(45, per)))

        def t_scoop(dst: List[Dict[str, Any]]):
            dst.extend(self._list_scoop(min(30, per)))

        th1 = threading.Thread(target=t_winget, args=(winget_rows,), daemon=True)
        th2 = threading.Thread(target=t_choco, args=(choco_rows,), daemon=True)
        th3 = threading.Thread(target=t_scoop, args=(scoop_rows,), daemon=True)
        for t in (th1, th2, th3):
            t.start()
        for t in (th1, th2, th3):
            t.join(timeout=per)

        all_rows = winget_rows + choco_rows + scoop_rows
        seen = set()
        merged = []
        for r in all_rows:
            key = (r.get("Id") or "", r.get("Source") or "")
            if key in seen:
                continue
            seen.add(key)
            merged.append(r)
        if merged:
            self._cache_write(merged)
        return merged

    def update_ids(self, ids: List[str]) -> Dict[str, List[str]]:
        results = {"updated": [], "interactive": [], "reinstalled": [], "skipped": [], "store_skipped": [], "failed": []}
        for pid in ids:
            if not looks_like_id(pid) or looks_like_version(pid):
                results["skipped"].append(pid)
                continue
            ok = False
            if self._has("winget"):
                rc = self.proc.run_stream(["winget","upgrade","--id",pid,"--silent","--disable-interactivity","--accept-source-agreements","--accept-package-agreements","--force"])
                ok = rc in (0,3010)
                if not ok:
                    rc2 = self.proc.run_stream(["winget","install","--id",pid,"--silent","--disable-interactivity","--accept-source-agreements","--accept-package-agreements","--force"])
                    ok = rc2 in (0,3010)
            if not ok and self._has("choco"):
                rc = self.proc.run_stream(["choco","upgrade",pid,"-y"])
                ok = (rc == 0)
            if not ok and self._has("scoop"):
                rc = self.proc.run_stream(["scoop","update",pid])
                ok = (rc == 0)
            (results["updated"] if ok else results["failed"]).append(pid)
        return results