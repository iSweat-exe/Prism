from fastapi import APIRouter
from . import cpu, disk, network, os, ram, uptime

router = APIRouter()

router.include_router(cpu.router, prefix="/cpu", tags=["System Cpu"])
router.include_router(ram.router, prefix="/ram", tags=["System Ram"])
router.include_router(disk.router, prefix="/disk", tags=["System Disk"])
router.include_router(network.router, prefix="/network", tags=["System Network"])
router.include_router(os.router, prefix="/os", tags=["System Os"])
router.include_router(uptime.router, prefix="/uptime", tags=["System Uptime"])
