import os

if os.path.exists("/host/proc"):
    os.environ["PROCFS_PATH"] = "/host/proc"

from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from routers.api import api_info
from routers import docker, system
from services.docker_service import docker_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize the docker client
    docker_service.init()
    yield
    # Shutdown: Close the docker client
    await docker_service.close()


app = FastAPI(
    redirect_slashes=False, title="PrismAPI", version="1.0.0", lifespan=lifespan
)

#! EDIT BEFORE PRODUCTION
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

v1 = APIRouter(prefix="/v1")

@v1.get("/system")
def get_system():
    return {
        "api": api_info(),
        "os": system.os.get_os(),
        "uptime": system.uptime.get_uptime(),
        "cpu": system.cpu.get_cpu(),
        "ram": system.ram.get_ram(),
        "disk": system.disk.get_disk(),
        "network": system.network.get_network(),
    }


v1.include_router(system.router, prefix="/system")
v1.include_router(docker.router, prefix="/docker")

app.include_router(v1)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
