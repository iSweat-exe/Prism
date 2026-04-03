from fastapi import APIRouter

from app.core.exceptions import PM2ServiceError
from app.modules.pm2.service import pm2_service

router = APIRouter()


@router.get("/{id_or_name}")
async def delete_process(id_or_name: str):
    """Delete a process from the PM2 list."""
    success = await pm2_service.process_action(id_or_name, "delete")
    if not success:
        raise PM2ServiceError(f"Failed to delete process '{id_or_name}'", status_code=500)
    return {"status": "success", "action": "delete", "target": id_or_name}


@router.post("/save")
async def save_config():
    """Save the current PM2 configuration."""
    success = await pm2_service.save_config()
    if not success:
        raise PM2ServiceError("Failed to save PM2 configuration", status_code=500)
    return {"status": "success", "message": "PM2 configuration saved"}
