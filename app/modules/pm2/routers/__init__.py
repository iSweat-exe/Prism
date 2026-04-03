from fastapi import APIRouter

from app.core.exceptions import PM2ServiceError
from app.modules.pm2.service import pm2_service

from . import actions, logs, manage

router = APIRouter()


@router.get("", tags=["PM2 List"])
async def list_pm2_processes():
    """Retrieve the list of all PM2 processes with status and performance metrics."""
    try:
        processes = await pm2_service.list_processes()
        if processes is None:
            raise PM2ServiceError("PM2 is not installed or the service is not started.")
        return processes
    except PM2ServiceError:
        raise
    except Exception as e:
        raise PM2ServiceError(f"An unexpected error occurred while retrieving PM2 processes: {str(e)}")


router.include_router(actions.router, tags=["PM2 Actions"])
router.include_router(manage.router, tags=["PM2 Management"])
router.include_router(logs.router, tags=["PM2 Logs"])
