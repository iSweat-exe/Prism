import os

from fastapi import APIRouter

from services.docker_service import docker_service
from services.pm2_service import pm2_service
from services.sampler import sampler
from services.uptime import get_app_uptime, get_app_uptime_formatted

router = APIRouter()


@router.get("")
async def api_info():
    """Returns a rich overview of the API and managed services."""
    # Docker Status
    docker_info = {"status": "offline", "containers": 0}
    if docker_service.client:
        try:
            containers = await docker_service.client.containers.list(all=True)
            docker_info = {"status": "online", "containers": len(containers)}
        except Exception:
            pass

    # PM2 Status
    pm2_info = {"status": "offline", "processes": 0}
    try:
        processes = await pm2_service.list_processes()
        if processes is not None:
            pm2_info = {"status": "online", "processes": len(processes)}
    except Exception:
        pass


    return {
        "app": {
            "name": "PrismAPI",
            "version": "1.0.0",
            "status": "running",
            "uptime_seconds": get_app_uptime(),
            "uptime": get_app_uptime_formatted(),
        },
        "services": {
            "docker": docker_info,
            "pm2": pm2_info,
        },
        "environment": {
            "is_container": os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv"),
            "procfs": os.getenv("PROCFS_PATH", "/proc"),
        },
    }
