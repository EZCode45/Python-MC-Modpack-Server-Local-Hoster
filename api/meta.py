from fastapi import APIRouter

import java as java_check
from loaders import fabric

router = APIRouter(prefix="/api/meta")


@router.get("/java")
def java_status():
    path = java_check.find_java()
    if path is None:
        return {"found": False}
    version = java_check.get_java_version(path)
    return {"found": True, "path": path, "version": version}


@router.get("/fabric/loader-versions/{mc_version}")
async def fabric_loader_versions(mc_version: str):
    versions = await fabric.get_loader_versions(mc_version)
    # return just the loader version strings, newest first
    return [v["loader"]["version"] for v in versions]
