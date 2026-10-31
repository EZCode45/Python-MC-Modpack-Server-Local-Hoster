import json
import os
import uuid
from dataclasses import dataclass, asdict

from config import INSTANCES_DIR, DATA_FILE, DEFAULT_RAM_MB, DEFAULT_MC_PORT


@dataclass
class Instance:
    id: str
    name: str
    loader: str          # "fabric" for V1
    mc_version: str
    loader_version: str
    ram_mb: int = DEFAULT_RAM_MB
    port: int = DEFAULT_MC_PORT
    eula_accepted: bool = False
    jar_name: str = "server.jar"

    @property
    def dir(self) -> str:
        return os.path.join(INSTANCES_DIR, self.id)


def _load_all() -> dict:
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        raw = json.load(f)
    return {k: Instance(**v) for k, v in raw.items()}


def _save_all(instances: dict):
    with open(DATA_FILE, "w") as f:
        json.dump({k: asdict(v) for k, v in instances.items()}, f, indent=2)


def list_instances() -> list[Instance]:
    return list(_load_all().values())


def get_instance(instance_id: str) -> Instance | None:
    return _load_all().get(instance_id)


def create_instance(name: str, loader: str, mc_version: str, loader_version: str,
                     ram_mb: int = DEFAULT_RAM_MB, port: int = DEFAULT_MC_PORT) -> Instance:
    instances = _load_all()

    # port conflict check
    if any(i.port == port for i in instances.values()):
        raise ValueError(f"Port {port} is already in use by another instance")

    inst = Instance(
        id=str(uuid.uuid4())[:8],
        name=name,
        loader=loader,
        mc_version=mc_version,
        loader_version=loader_version,
        ram_mb=ram_mb,
        port=port,
    )
    setup_instance_folder(inst.dir)
    instances[inst.id] = inst
    _save_all(instances)
    return inst


def update_instance(instance_id: str, **changes) -> Instance:
    instances = _load_all()
    inst = instances.get(instance_id)
    if inst is None:
        raise KeyError("Instance not found")
    for key, value in changes.items():
        setattr(inst, key, value)
    instances[instance_id] = inst
    _save_all(instances)
    return inst


def delete_instance(instance_id: str):
    instances = _load_all()
    instances.pop(instance_id, None)
    _save_all(instances)


def setup_instance_folder(instance_dir: str):
    """Create the instance folder. EULA is NOT written here —
    it must only be written after the user explicitly agrees in the UI."""
    os.makedirs(instance_dir, exist_ok=True)


def write_eula(instance_id: str):
    """Call this only after explicit user confirmation of the Minecraft EULA."""
    inst = get_instance(instance_id)
    if inst is None:
        raise KeyError("Instance not found")
    eula_path = os.path.join(inst.dir, "eula.txt")
    with open(eula_path, "w") as f:
        f.write("eula=true\n")
    update_instance(instance_id, eula_accepted=True)
