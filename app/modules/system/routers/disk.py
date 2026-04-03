import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.logger import logger
from app.modules.system.sampler import sampler

router = APIRouter(
    responses={
        500: {
            "description": "Internal error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "internal_server_error",
                        "message": "Error details",
                        "path": "/system/disk",
                    }
                }
            },
        }
    }
)


def fetch_disk_data():
    disk_cache = sampler.get_disks()
    partitions = disk_cache["disks"]

    if not partitions:
        raise RuntimeError("Disk partitions inaccessible")

    return {
        "global_io_read_bps": disk_cache["io"]["read_bytes"],
        "global_io_written_bps": disk_cache["io"]["write_bytes"],
        "disks": partitions,
    }


@router.get("")
def get_disk():
    try:
        return fetch_disk_data()

    except RuntimeError as e:
        logger.error(f"Runtime error in get_disk: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "disk_data_unavailable",
                "message": "Unable to retrieve disk data",
                "path": "/system/disk",
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_disk: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
                "path": "/system/disk",
            },
        )


async def disk_streamer():
    while True:
        try:
            data = fetch_disk_data()
            yield f"data: {json.dumps(data)}\n\n"
        except Exception as e:
            logger.error(f"Error in disk_streamer: {e}")
            yield f"data: {json.dumps({'error': 'stream_interrupted', 'message': 'Unable to stream disk data'})}\n\n"
        await asyncio.sleep(1)


@router.get("/stream")
async def stream_disk():
    return StreamingResponse(disk_streamer(), media_type="text/event-stream")
