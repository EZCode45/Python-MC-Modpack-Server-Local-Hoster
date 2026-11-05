from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import instances as inst_store
from api.instances import supervisor

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.get("/create", response_class=HTMLResponse)
def create_page(request: Request):
    return templates.TemplateResponse(request, "create.html")


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse(request, "settings.html")


@router.get("/instances/{instance_id}", response_class=HTMLResponse)
def instance_page(request: Request, instance_id: str):
    inst = inst_store.get_instance(instance_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Instance not found")
    return templates.TemplateResponse(request, "instance.html", {"inst": inst})


@router.get("/partials/instances", response_class=HTMLResponse)
def instances_partial(request: Request):
    data = []
    for inst in inst_store.list_instances():
        proc = supervisor.get(inst.id)
        data.append({**inst.__dict__, "running": proc.is_running() if proc else False})
    return templates.TemplateResponse(request, "_instances.html", {"instances": data})