from fastapi import FastAPI
import uvicorn

from api.instances import router as instances_router

app = FastAPI()
app.include_router(instances_router)


@app.get("/")
def home():
    return {"status": "dashboard alive"}


def main():
    uvicorn.run(app, host="127.0.0.1", port=8080)


if __name__ == "__main__":
    main()