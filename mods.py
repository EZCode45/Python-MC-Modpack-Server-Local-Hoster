import json
import os
import hashlib

import httpx

from packs.modrinth import HEADERS

MODS_SUBDIR = "mods"
REGISTRY_FILENAME = "mods.json"


def _registry_path(instance_dir: str) -> str:
    return os.path.join(instance_dir, REGISTRY_FILENAME)


def _load_registry(instance_dir: str) -> dict:
    path = _registry_path(instance_dir)
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def _save_registry(instance_dir: str, registry: dict):
    with open(_registry_path(instance_dir), "w") as f:
        json.dump(registry, f, indent=2)


def list_installed(instance_dir: str) -> list[dict]:
    """Return the list of mods tracked for this instance."""
    return list(_load_registry(instance_dir).values())


def _sha1_of(path: str) -> str:
    sha1 = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha1.update(chunk)
    return sha1.hexdigest()


async def install_mod(instance_dir: str, project_id: str, title: str, version_id: str,
                       version_number: str, filename: str, file_url: str,
                       expected_sha1: str | None = None) -> dict:
    """Download a mod jar into the instance's mods/ folder and record it
    in the registry. If a mod from the same project is already installed,
    its old jar is removed first (this is effectively an update too)."""
    mods_dir = os.path.join(instance_dir, MODS_SUBDIR)
    os.makedirs(mods_dir, exist_ok=True)

    registry = _load_registry(instance_dir)

    # remove any existing jar for this project first (covers both fresh
    # installs replacing a stale file and explicit updates)
    existing = registry.get(project_id)
    if existing:
        old_path = os.path.join(mods_dir, existing["filename"])
        if os.path.isfile(old_path):
            os.remove(old_path)

    dest_path = os.path.join(mods_dir, filename)
    async with httpx.AsyncClient(headers=HEADERS) as client:
        r = await client.get(file_url)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(r.content)

    if expected_sha1:
        actual = _sha1_of(dest_path)
        if actual != expected_sha1:
            os.remove(dest_path)
            raise ValueError(f"Hash mismatch for {filename} — download may be corrupt")

    entry = {
        "project_id": project_id,
        "title": title,
        "version_id": version_id,
        "version_number": version_number,
        "filename": filename,
    }
    registry[project_id] = entry
    _save_registry(instance_dir, registry)
    return entry


def remove_mod(instance_dir: str, project_id: str):
    registry = _load_registry(instance_dir)
    entry = registry.pop(project_id, None)
    if entry is None:
        raise KeyError("Mod not installed on this instance")

    jar_path = os.path.join(instance_dir, MODS_SUBDIR, entry["filename"])
    if os.path.isfile(jar_path):
        os.remove(jar_path)

    _save_registry(instance_dir, registry)