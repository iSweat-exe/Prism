from fastapi import APIRouter
from . import containers, images

router = APIRouter()

router.include_router(containers.router, prefix="/containers", tags=["Docker Containers"])
router.include_router(images.router, prefix="/images", tags=["Docker Images"])
