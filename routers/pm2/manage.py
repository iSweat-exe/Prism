from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.pm2_service import pm2_service

router = APIRouter()


@router.delete("/{id_or_name}")
async def delete_process(id_or_name: str):
    """Delete a process from the PM2 list."""
    success = await pm2_service.process_action(id_or_name, "delete")
    if not success:
        return JSONResponse(
            status_code=500,
            content={
                "error": "pm2_delete_failed",
                "message": f"Failed to delete process '{id_or_name}'",
                "path": f"/v1/pm2/{id_or_name}",
            },
        )
    return {"status": "success", "action": "delete", "target": id_or_name}


@router.post("/save")
async def save_config():
    """Save the current PM2 configuration."""
    success = await pm2_service.save_config()
    if not success:
        return JSONResponse(
            status_code=500,
            content={
                "error": "pm2_save_failed",
                "message": "Failed to save PM2 configuration",
                "path": "/v1/pm2/save",
            },
        )
    return {"status": "success", "message": "PM2 configuration saved"}
