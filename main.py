from fastapi import APIRouter, FastAPI

from middleware import setup_middleware
from routers import docker, pm2, system
from services.lifespan import lifespan

app = FastAPI(
    redirect_slashes=False,
    title="PrismAPI",
    version="1.0.0",
    lifespan=lifespan,
)

setup_middleware(app)

api_router = APIRouter(prefix="/v1")

api_router.include_router(system.router, prefix="/system")
api_router.include_router(docker.router, prefix="/docker")
api_router.include_router(pm2.router, prefix="/pm2")

app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8081)
