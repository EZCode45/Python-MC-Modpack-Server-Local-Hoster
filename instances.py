import os

def setup_instance_folder(instance_dir: str):
    """Create the instance folder. EULA is NOT written here —
    it must only be written after the user explicitly agrees in the UI."""
    os.makedirs(instance_dir, exist_ok=True)

def write_eula(instance_dir: str):
    """Call this only after explicit user confirmation of the Minecraft EULA."""
    eula_path = os.path.join(instance_dir, "eula.txt")
    with open(eula_path, "w") as f:
        f.write("eula=true\n")