from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.exceptions import PM2ServiceError
from app.modules.pm2.service import pm2_service

router = APIRouter()


@router.get("/{id_or_name}/logs")
async def get_process_logs(id_or_name: str, lines: int = Query(100, ge=1, le=1000)):
    """Fetch the last N lines of logs for a process."""
    try:
        return await pm2_service.get_logs(id_or_name, lines)
    except Exception as e:
        raise PM2ServiceError(f"Failed to fetch logs for process '{id_or_name}': {str(e)}")


@router.get("/{id_or_name}/logs/stream")
async def stream_process_logs(id_or_name: str):
    """Stream real-time logs for a process using SSE."""
    return StreamingResponse(
        pm2_service.log_streamer(id_or_name),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
