import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCES_DIR = os.path.join(BASE_DIR, "instances")
DATA_FILE = os.path.join(BASE_DIR, "data.json")

DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 8080

DEFAULT_RAM_MB = 2048
DEFAULT_MC_PORT = 25565

os.makedirs(INSTANCES_DIR, exist_ok=True)
