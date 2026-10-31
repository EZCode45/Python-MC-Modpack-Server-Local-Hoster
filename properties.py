import os


def read_properties(instance_dir: str) -> dict:
    path = os.path.join(instance_dir, "server.properties")
    props = {}
    if not os.path.exists(path):
        return props
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                props[key.strip()] = value.strip()
    return props


def write_properties(instance_dir: str, props: dict):
    path = os.path.join(instance_dir, "server.properties")
    # preserve existing values not being changed
    existing = read_properties(instance_dir)
    existing.update(props)
    with open(path, "w") as f:
        for key, value in existing.items():
            f.write(f"{key}={value}\n")


def ensure_defaults(instance_dir: str, port: int):
    """Write sane defaults the first time, including the chosen port,
    whitelist on, and online-mode on by default for security."""
    defaults = {
        "server-port": str(port),
        "white-list": "true",
        "online-mode": "true",
        "motd": "A Minecraft Server",
    }
    existing = read_properties(instance_dir)
    for key, value in defaults.items():
        existing.setdefault(key, value)
    write_properties(instance_dir, existing)
