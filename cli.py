import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

from config import DASHBOARD_HOST, DASHBOARD_PORT
from api.instances import router as instances_router
from api.meta import router as meta_router
from api.pages import router as pages_router
import server as server_module


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Sync endpoints run in worker threads with no event loop of their own,
    # so ServerProcess needs this captured once, up front, to broadcast
    # console output back to WebSocket subscribers safely.
    server_module.set_main_loop(asyncio.get_running_loop())
    yield
    # (nothing needed on shutdown yet)


app = FastAPI(title="MC Server Hoster", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages_router)
app.include_router(instances_router)
app.include_router(meta_router)


def main():
    uvicorn.run(app, host=DASHBOARD_HOST, port=DASHBOARD_PORT)


if __name__ == "__main__":
    main()