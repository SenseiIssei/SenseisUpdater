import json
from ..data.paths import CONFIG_DIR, CONFIG_PATH

class ConfigStore:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self):
        if CONFIG_PATH.exists():
            try:
                return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def save(self):
        tmp = CONFIG_PATH.with_suffix(".tmp.json")
        tmp.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        tmp.replace(CONFIG_PATH)

    def list_profiles(self):
        return sorted(self.data.get("profiles", {}).keys())

    def get_profile(self, name: str):
        return set(self.data.get("profiles", {}).get(name, []))

    def set_profile(self, name: str, ids):
        self.data.setdefault("profiles", {})[name] = sorted(set(ids))
        self.save()