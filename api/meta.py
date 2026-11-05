import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import java as java_check
import config
from loaders import fabric

router = APIRouter(prefix="/api/meta")


@router.get("/java")
def java_status():
    path = java_check.find_java()
    if path is None:
        return {"found": False}
    version = java_check.get_java_version(path)
    return {"found": True, "path": path, "version": version}


class JavaPathRequest(BaseModel):
    path: str


@router.post("/java/override")
def set_java_path(req: JavaPathRequest):
    if not os.path.isfile(req.path):
        raise HTTPException(status_code=400, detail="That file doesn't exist")
    config.set_java_override(req.path)
    return {"status": "saved", "path": req.path}


@router.delete("/java/override")
def clear_java_path():
    config.set_java_override(None)
    return {"status": "cleared"}


@router.get("/fabric/loader-versions/{mc_version}")
async def fabric_loader_versions(mc_version: str):
    versions = await fabric.get_loader_versions(mc_version)
    # return just the loader version strings, newest first
    return [v["loader"]["version"] for v in versions]