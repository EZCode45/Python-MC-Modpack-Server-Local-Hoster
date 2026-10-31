from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

from config import DASHBOARD_HOST, DASHBOARD_PORT
from api.instances import router as instances_router
from api.meta import router as meta_router
from api.pages import router as pages_router

app = FastAPI(title="MC Server Hoster")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages_router)
app.include_router(instances_router)
app.include_router(meta_router)


def main():
    uvicorn.run(app, host=DASHBOARD_HOST, port=DASHBOARD_PORT)


if __name__ == "__main__":
    main()
