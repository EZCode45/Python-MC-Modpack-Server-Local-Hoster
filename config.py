import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCES_DIR = os.path.join(BASE_DIR, "instances")
DATA_FILE = os.path.join(BASE_DIR, "data.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 8080

DEFAULT_RAM_MB = 2048
DEFAULT_MC_PORT = 25565

os.makedirs(INSTANCES_DIR, exist_ok=True)


def get_java_override() -> str | None:
    """A manually-set path to java.exe, stored via the dashboard settings.
    Takes priority over auto-detection when present."""
    if not os.path.exists(SETTINGS_FILE):
        return None
    with open(SETTINGS_FILE, "r") as f:
        settings = json.load(f)
    return settings.get("java_path") or None


def set_java_override(path: str | None):
    settings = {}
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
    settings["java_path"] = path
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)