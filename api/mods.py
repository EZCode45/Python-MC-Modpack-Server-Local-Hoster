from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import instances as inst_store
import mods as mods_store
from packs import modrinth

router = APIRouter(prefix="/api/instances/{instance_id}/mods")


def _require_instance(instance_id: str):
    inst = inst_store.get_instance(instance_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Instance not found")
    return inst


@router.get("")
def list_mods(instance_id: str):
    inst = _require_instance(instance_id)
    return mods_store.list_installed(inst.dir)


class InstallModRequest(BaseModel):
    project_id: str
    title: str
    version_id: str
    version_number: str
    filename: str
    file_url: str
    file_sha1: str | None = None


@router.post("")
async def install_mod(instance_id: str, req: InstallModRequest):
    inst = _require_instance(instance_id)
    try:
        entry = await mods_store.install_mod(
            instance_dir=inst.dir,
            project_id=req.project_id,
            title=req.title,
            version_id=req.version_id,
            version_number=req.version_number,
            filename=req.filename,
            file_url=req.file_url,
            expected_sha1=req.file_sha1,
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return entry


@router.delete("/{project_id}")
def remove_mod(instance_id: str, project_id: str):
    inst = _require_instance(instance_id)
    try:
        mods_store.remove_mod(inst.dir, project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Mod not installed on this instance")
    return {"status": "removed"}


@router.get("/updates")
async def check_updates(instance_id: str):
    """For each installed mod, check whether a newer version exists for
    this instance's Minecraft version and loader."""
    inst = _require_instance(instance_id)
    installed = mods_store.list_installed(inst.dir)

    updates = []
    for mod in installed:
        versions = await modrinth.get_mod_versions(
            mod["project_id"], inst.mc_version, loader=inst.loader
        )
        if not versions:
            continue
        latest = versions[0]
        if latest["version_id"] != mod["version_id"]:
            updates.append({
                "project_id": mod["project_id"],
                "title": mod["title"],
                "current_version": mod["version_number"],
                "latest_version": latest["version_number"],
                "latest": latest,
            })
    return updates