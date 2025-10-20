from pathlib import Path
import os

APP_NAME = "SenseiUpdater"
KO_FI_URL = "https://ko-fi.com/senseiissei"

CONFIG_DIR = Path(os.getenv("LOCALAPPDATA", Path.home())) / APP_NAME
CONFIG_PATH = CONFIG_DIR / "config.json"