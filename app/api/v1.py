from fastapi import APIRouter

from app.modules.docker.routers import router as docker_router
from app.modules.pm2.routers import router as pm2_router
from app.modules.system.routers import router as system_router

router = APIRouter()

router.include_router(system_router, prefix="/system")
router.include_router(docker_router, prefix="/docker")
router.include_router(pm2_router, prefix="/pm2")
