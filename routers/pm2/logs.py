from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse

from services.logger import logger
from services.pm2_service import pm2_service

router = APIRouter()


@router.get("/{id_or_name}/logs")
async def get_process_logs(id_or_name: str, lines: int = Query(100, ge=1, le=1000)):
    """Fetch the last N lines of logs for a process."""
    try:
        logs = await pm2_service.get_logs(id_or_name, lines)
        return logs
    except Exception as e:
        logger.error(f"Error fetching logs for {id_or_name}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "logs_fetch_failed",
                "message": f"Failed to fetch logs for process '{id_or_name}'",
                "path": f"/v1/pm2/{id_or_name}/logs",
            },
        )


@router.get("/{id_or_name}/logs/stream")
async def stream_process_logs(id_or_name: str):
    """Stream real-time logs for a process using SSE."""
    return StreamingResponse(
        pm2_service.log_streamer(id_or_name),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
