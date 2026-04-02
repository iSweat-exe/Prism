from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.pm2_service import pm2_service

router = APIRouter()


async def execute_pm2_action(id_or_name: str, action: str):
    """Helper to execute a PM2 action and return a standardized response."""
    success = await pm2_service.process_action(id_or_name, action)
    if not success:
        return JSONResponse(
            status_code=500,
            content={
                "error": "pm2_action_failed",
                "message": f"Failed to {action} process '{id_or_name}'",
                "path": f"/v1/pm2/{id_or_name}/{action}",
            },
        )
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
