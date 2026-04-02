from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.logger import logger
from services.pm2_service import pm2_service

from . import actions, logs, manage

router = APIRouter()


@router.get("", tags=["PM2 List"])
async def list_pm2_processes():
    """Retrieve the list of all PM2 processes with status and performance metrics."""
    try:
        processes = await pm2_service.list_processes()
        if processes is None:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "pm2_not_running",
                    "message": "PM2 is not installed or the service is not started.",
                    "path": "/v1/pm2",
                },
            )
        return processes
    except Exception as e:
        logger.error(f"Unexpected error in list_pm2_processes: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred while retrieving PM2 processes",
                "path": "/v1/pm2",
            },
        )


router.include_router(actions.router, tags=["PM2 Actions"])
router.include_router(manage.router, tags=["PM2 Management"])
router.include_router(logs.router, tags=["PM2 Logs"])
