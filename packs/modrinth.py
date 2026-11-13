import hashlib
import json
import os
import zipfile
import shutil
import tempfile

import httpx

MODRINTH_API = "https://api.modrinth.com/v2"

# Modrinth asks all API clients to identify themselves with a descriptive
# User-Agent, per their API etiquette guidelines.
HEADERS = {
    "User-Agent": "mc-server-hoster/0.2 (github.com/EZCode45/Python-MC-Modpack-Server-Local-Hoster)"
}


async def search_modpacks(query: str, limit: int = 15) -> list[dict]:
    """Search Modrinth for modpacks matching the query."""
    params = {
        "query": query,
        "limit": limit,
        "facets": json.dumps([["project_type:modpack"]]),
    }
    async with httpx.AsyncClient(headers=HEADERS) as client:
        r = await client.get(f"{MODRINTH_API}/search", params=params)
        r.raise_for_status()
        data = r.json()

    return [
        {
            "project_id": hit["project_id"],
            "slug": hit["slug"],
            "title": hit["title"],
            "description": hit["description"],
            "icon_url": hit.get("icon_url"),
            "downloads": hit.get("downloads", 0),
        }
        for hit in data.get("hits", [])
    ]


async def get_pack_versions(project_id: str, loader: str = "fabric") -> list[dict]:
    """List a modpack's versions compatible with the given loader, newest first."""
    params = {"loaders": json.dumps([loader])}
    async with httpx.AsyncClient(headers=HEADERS) as client:
        r = await client.get(f"{MODRINTH_API}/project/{project_id}/version", params=params)
        r.raise_for_status()
        versions = r.json()

    result = []
    for v in versions:
        mrpack_file = next((f for f in v["files"] if f["primary"]), None)
        if mrpack_file is None:
            continue
        result.append({
            "version_id": v["id"],
            "version_number": v["version_number"],
            "name": v["name"],
            "game_versions": v.get("game_versions", []),
            "loaders": v.get("loaders", []),
            "file_url": mrpack_file["url"],
            "file_sha1": mrpack_file["hashes"].get("sha1"),
        })
    return result


async def search_mods(query: str, limit: int = 15) -> list[dict]:
    """Search Modrinth for individual mods (not modpacks) matching the query."""
    params = {
        "query": query,
        "limit": limit,
        "facets": json.dumps([["project_type:mod"]]),
    }
    async with httpx.AsyncClient(headers=HEADERS) as client:
        r = await client.get(f"{MODRINTH_API}/search", params=params)
        r.raise_for_status()
        data = r.json()

    return [
        {
            "project_id": hit["project_id"],
            "slug": hit["slug"],
            "title": hit["title"],
            "description": hit["description"],
            "icon_url": hit.get("icon_url"),
            "downloads": hit.get("downloads", 0),
        }
        for hit in data.get("hits", [])
    ]


async def get_mod_versions(project_id: str, mc_version: str, loader: str = "fabric") -> list[dict]:
    """List a mod's versions compatible with the given Minecraft version and loader,
    newest first. Also includes each version's dependencies, per the plan's note
    to check each mod's dependencies when adding mods/plugins."""
    params = {
        "loaders": json.dumps([loader]),
        "game_versions": json.dumps([mc_version]),
    }
    async with httpx.AsyncClient(headers=HEADERS) as client:
        r = await client.get(f"{MODRINTH_API}/project/{project_id}/version", params=params)
        r.raise_for_status()
        versions = r.json()

    result = []
    for v in versions:
        primary_file = next((f for f in v["files"] if f["primary"]), None)
        if primary_file is None:
            continue
        result.append({
            "version_id": v["id"],
            "version_number": v["version_number"],
            "name": v["name"],
            "game_versions": v.get("game_versions", []),
            "loaders": v.get("loaders", []),
            "filename": primary_file["filename"],
            "file_url": primary_file["url"],
            "file_sha1": primary_file["hashes"].get("sha1"),
            "dependencies": v.get("dependencies", []),
        })
    return result


async def get_project(project_id: str) -> dict:
    """Fetch basic project info (title, slug) — used to display a friendly
    name for an installed mod without re-searching."""
    async with httpx.AsyncClient(headers=HEADERS) as client:
        r = await client.get(f"{MODRINTH_API}/project/{project_id}")
        r.raise_for_status()
        data = r.json()
    return {"project_id": data["id"], "slug": data["slug"], "title": data["title"]}


async def download_mrpack(file_url: str, dest_path: str):
    """Download the .mrpack file itself (a zip) to dest_path."""
    async with httpx.AsyncClient(headers=HEADERS) as client:
        async with client.stream("GET", file_url) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                async for chunk in r.aiter_bytes():
                    f.write(chunk)


def _sha1_matches(path: str, expected_hex: str | None) -> bool:
    if not expected_hex:
        return True  # nothing to verify against
    sha1 = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha1.update(chunk)
    return sha1.hexdigest() == expected_hex


async def install_modpack(instance_dir: str, mrpack_path: str) -> dict:
    """Extract modrinth.index.json, download server-relevant mod files with
    hash verification, and apply overrides. Returns the index's dependency
    info (minecraft version, loader version) so the caller can match jar install."""
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(mrpack_path, "r") as z:
            z.extractall(tmp)

        index_path = os.path.join(tmp, "modrinth.index.json")
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)

        # Download each file whose server environment isn't explicitly unsupported.
        async with httpx.AsyncClient(headers=HEADERS) as client:
            for file_entry in index.get("files", []):
                env = file_entry.get("env", {})
                if env.get("server") == "unsupported":
                    continue  # client-only mod, skip

                rel_path = file_entry["path"]
                dest_path = os.path.join(instance_dir, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                download_url = file_entry["downloads"][0]
                r = await client.get(download_url)
                r.raise_for_status()
                with open(dest_path, "wb") as out:
                    out.write(r.content)

                expected_sha1 = file_entry.get("hashes", {}).get("sha1")
                if not _sha1_matches(dest_path, expected_sha1):
                    raise ValueError(f"Hash mismatch for {rel_path} — download may be corrupt")

        # Apply overrides, then server-overrides on top (server-overrides wins).
        overrides_dir = os.path.join(tmp, "overrides")
        if os.path.isdir(overrides_dir):
            _copy_tree_merge(overrides_dir, instance_dir)

        server_overrides_dir = os.path.join(tmp, "server-overrides")
        if os.path.isdir(server_overrides_dir):
            _copy_tree_merge(server_overrides_dir, instance_dir)

        return index.get("dependencies", {})


def _copy_tree_merge(src: str, dst: str):
    """Copy src's contents into dst, overwriting files that already exist."""
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target_root = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(target_root, exist_ok=True)
        for name in files:
            shutil.copy2(os.path.join(root, name), os.path.join(target_root, name)) 