import time
from datetime import datetime, timezone

import psutil
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(
    responses={
        500: {
            "description": "Internal error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "internal_server_error",
                        "message": "Error details",
                        "path": "/system/uptime",
                    }
                }
            },
        }
    }
)


def format_uptime(uptime_secs: int) -> str:
    try:
        hours, remainder = divmod(uptime_secs, 3600)
        minutes, seconds = divmod(remainder, 60)
        days = hours // 24
        hours = hours % 24
        return f"{days}d {hours}h {minutes}m {seconds}s"
    except Exception:
        return "Unknown"


def get_boot_time_iso(boot_time: float) -> str:
    try:
        return datetime.fromtimestamp(boot_time, tz=timezone.utc).isoformat()
    except Exception:
        return "Unknown"


@router.get("")
def get_uptime():
    try:
        boot_time = psutil.boot_time()

        if not boot_time or boot_time <= 0:
            raise RuntimeError("Unable to retrieve boot time")

        uptime_secs = int(time.time() - boot_time)

        if uptime_secs < 0:
            raise RuntimeError(f"Invalid uptime: {uptime_secs}s")

        return {
            "uptime_secs": uptime_secs,
            "boot_time": get_boot_time_iso(boot_time),
            "uptime_formatted": format_uptime(uptime_secs),
        }

    except RuntimeError as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "uptime_data_unavailable",
                "message": str(e),
                "path": "/system/uptime",
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": str(e),
                "path": "/system/uptime",
            },
        )
