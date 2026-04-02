import platform
import socket

import psutil
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from services.logger import logger

router = APIRouter(
    responses={
        500: {
            "description": "Internal error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "internal_server_error",
                        "message": "Error details",
                        "path": "/system/os",
                    }
                }
            },
        }
    }
)


def get_load_average() -> tuple:
    try:
        return psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0.0, 0.0, 0.0)
    except Exception:
        return (0.0, 0.0, 0.0)


def get_kernel_version() -> str:
    try:
        return platform.version().split(".")[2].split(" ")[0]
    except IndexError, AttributeError:
        return platform.version() or "Unknown"


def get_hostname() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return "Unknown"


@router.get("")
def get_os():
    try:
        load_avg = get_load_average()

        return {
            "hostname": get_hostname(),
            "os_name": platform.system() or "Unknown",
            "os_version": f"{platform.system()} {platform.release()}".strip() or "Unknown",
            "kernel_version": get_kernel_version(),
            "arch": platform.machine() or "Unknown",
            "distribution_id": platform.system().lower() or "unknown",
            "load_average": {
                "one": load_avg[0],
                "five": load_avg[1],
                "fifteen": load_avg[2],
            },
        }

    except Exception as e:
        logger.error(f"Unexpected error in get_os: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "Unable to retrieve system OS information",
                "path": "/system/os",
            },
        )
