from fastapi import APIRouter

from app.core.exceptions import PM2ServiceError
from app.modules.pm2.service import pm2_service

router = APIRouter()


async def execute_pm2_action(id_or_name: str, action: str):
    """Helper to execute a PM2 action and return a standardized response."""
    success = await pm2_service.process_action(id_or_name, action)
    if not success:
        raise PM2ServiceError(f"Failed to {action} process '{id_or_name}'", status_code=500)
    return {"status": "success", "action": action, "target": id_or_name}


@router.post("/{id_or_name}/start")
async def start_process(id_or_name: str):
    return await execute_pm2_action(id_or_name, "start")


@router.post("/{id_or_name}/stop")
async def stop_process(id_or_name: str):
    return await execute_pm2_action(id_or_name, "stop")


@router.post("/{id_or_name}/restart")
async def restart_process(id_or_name: str):
    return await execute_pm2_action(id_or_name, "restart")


@router.post("/{id_or_name}/reload")
async def reload_process(id_or_name: str):
    return await execute_pm2_action(id_or_name, "reload")
