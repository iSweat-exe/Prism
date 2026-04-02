import os
import time
import traceback

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import docker, pm2, system
from routers.api import api_info
from services.docker_service import docker_service
from services.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting PrismAPI...")
    docker_service.init()
    yield
    logger.info("Stopping PrismAPI...")
    await docker_service.close()


app = FastAPI(redirect_slashes=False, title="PrismAPI", version="1.0.0", lifespan=lifespan)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)")
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred.",
        },
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
async def get_system():
    return {
        "api": await api_info(),
        "os": system.os.get_os(),
        "uptime": system.uptime.get_uptime(),
        "cpu": system.cpu.get_cpu(),
        "ram": system.ram.get_ram(),
        "disk": system.disk.get_disk(),
        "network": system.network.get_network(),
    }


v1.include_router(system.router, prefix="/system")
v1.include_router(docker.router, prefix="/docker")
v1.include_router(pm2.router, prefix="/pm2")

app.include_router(v1)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8081)
