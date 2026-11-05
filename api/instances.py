import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

import os

import instances as inst_store
import properties as props_store
from server import ServerProcess
from loaders import fabric

router = APIRouter(prefix="/api/instances")

# In-memory supervisor: instance_id -> ServerProcess
# Rebuilt from disk-backed instance data each run; processes themselves
# don't survive a restart of this program (by design — see "closing the
# program" behavior).
supervisor: dict[str, ServerProcess] = {}


def _get_or_create_process(instance_id: str) -> ServerProcess:
    if instance_id not in supervisor:
        inst = inst_store.get_instance(instance_id)
        if inst is None:
            raise HTTPException(status_code=404, detail="Instance not found")
        supervisor[instance_id] = ServerProcess(
            instance_dir=inst.dir,
            jar_name=inst.jar_name,
            ram_mb=inst.ram_mb,
        )
    return supervisor[instance_id]


class CreateInstanceRequest(BaseModel):
    name: str
    mc_version: str
    loader_version: str
    ram_mb: int = 2048
    port: int = 25565


@router.get("")
def list_instances():
    result = []
    for inst in inst_store.list_instances():
        proc = supervisor.get(inst.id)
        result.append({
            **inst.__dict__,
            "running": proc.is_running() if proc else False,
        })
    return result


@router.post("")
async def create_instance(req: CreateInstanceRequest):
    try:
        inst = inst_store.create_instance(
            name=req.name,
            loader="fabric",
            mc_version=req.mc_version,
            loader_version=req.loader_version,
            ram_mb=req.ram_mb,
            port=req.port,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    props_store.ensure_defaults(inst.dir, inst.port)

    # download the Fabric server jar for this instance
    installer_version = await fabric.get_latest_installer_version()
    jar_path = os.path.join(inst.dir, inst.jar_name)
    await fabric.download_server_jar(
        mc_version=req.mc_version,
        loader_version=req.loader_version,
        installer_version=installer_version,
        dest_path=jar_path,
    )

    return inst.__dict__


@router.post("/{instance_id}/accept-eula")
def accept_eula(instance_id: str):
    try:
        inst_store.write_eula(instance_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Instance not found")
    return {"eula_accepted": True}


@router.post("/{instance_id}/start")
def start_instance(instance_id: str):
    inst = inst_store.get_instance(instance_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Instance not found")
    if not inst.eula_accepted:
        raise HTTPException(status_code=400, detail="EULA not accepted")
    proc = _get_or_create_process(instance_id)
    if proc.is_running():
        raise HTTPException(status_code=400, detail="Already running")
    try:
        proc.start()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "started"}


@router.post("/{instance_id}/stop")
def stop_instance(instance_id: str):
    proc = supervisor.get(instance_id)
    if proc is None or not proc.is_running():
        raise HTTPException(status_code=400, detail="Not running")
    proc.stop()
    return {"status": "stopped"}


@router.post("/{instance_id}/restart")
def restart_instance(instance_id: str):
    proc = supervisor.get(instance_id)
    if proc is None:
        raise HTTPException(status_code=404, detail="Instance not found")
    try:
        proc.restart()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "restarted"}


@router.get("/{instance_id}/status")
def instance_status(instance_id: str):
    inst = inst_store.get_instance(instance_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Instance not found")
    proc = supervisor.get(instance_id)
    return {"running": proc.is_running() if proc else False}


class CommandRequest(BaseModel):
    command: str


@router.post("/{instance_id}/command")
def send_command(instance_id: str, req: CommandRequest):
    proc = supervisor.get(instance_id)
    if proc is None or not proc.is_running():
        raise HTTPException(status_code=400, detail="Not running")
    proc.send_command(req.command)
    return {"status": "sent"}


@router.get("/{instance_id}/properties")
def get_properties(instance_id: str):
    inst = inst_store.get_instance(instance_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Instance not found")
    return props_store.read_properties(inst.dir)


@router.put("/{instance_id}/properties")
def set_properties(instance_id: str, props: dict):
    inst = inst_store.get_instance(instance_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Instance not found")
    props_store.write_properties(inst.dir, props)
    return {"status": "saved"}


@router.websocket("/{instance_id}/console")
async def console_ws(websocket: WebSocket, instance_id: str):
    await websocket.accept()
    proc = supervisor.get(instance_id)
    if proc is None:
        await websocket.send_text("[instance not running yet]")
        await websocket.close()
        return

    # replay recent history first
    for line in list(proc.console_buffer):
        await websocket.send_text(line)

    queue = proc.subscribe()
    try:
        while True:
            # listen for either a new console line or an incoming command
            receive_task = asyncio.create_task(websocket.receive_text())
            queue_task = asyncio.create_task(queue.get())
            done, pending = await asyncio.wait(
                {receive_task, queue_task}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            if receive_task in done:
                command = receive_task.result()
                proc.send_command(command)
            if queue_task in done:
                await websocket.send_text(queue_task.result())
    except WebSocketDisconnect:
        pass
    finally:
        proc.unsubscribe(queue)