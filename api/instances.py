from fastapi import APIRouter, HTTPException
from server import ServerProcess

router = APIRouter(prefix="/api/instances")

# In-memory supervisor: instance_id -> ServerProcess
# (will move to a dedicated InstanceManager once step 3+ needs it)
supervisor: dict[str, ServerProcess] = {}


@router.post("/{instance_id}/start")
def start_instance(instance_id: str):
    proc = supervisor.get(instance_id)
    if proc is None:
        raise HTTPException(status_code=404, detail="Instance not found")
    if proc.is_running():
        raise HTTPException(status_code=400, detail="Already running")
    proc.start()
    return {"status": "started"}


@router.post("/{instance_id}/stop")
def stop_instance(instance_id: str):
    proc = supervisor.get(instance_id)
    if proc is None:
        raise HTTPException(status_code=404, detail="Instance not found")
    if not proc.is_running():
        raise HTTPException(status_code=400, detail="Not running")
    proc.stop()
    return {"status": "stopped"}


@router.get("/{instance_id}/status")
def instance_status(instance_id: str):
    proc = supervisor.get(instance_id)
    if proc is None:
        raise HTTPException(status_code=404, detail="Instance not found")
    return {"running": proc.is_running()}