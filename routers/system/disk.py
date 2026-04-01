import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from services.sampler import sampler

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
        raise RuntimeError("No accessible disk partitions found")

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
        return JSONResponse(
            status_code=500,
            content={
                "error": "disk_data_unavailable",
                "message": str(e),
                "path": "/system/disk",
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": str(e),
                "path": "/system/disk",
            },
        )


async def disk_streamer():
    while True:
        try:
            data = fetch_disk_data()
            yield f"data: {json.dumps(data)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        await asyncio.sleep(1)


@router.get("/stream")
async def stream_disk():
    return StreamingResponse(disk_streamer(), media_type="text/event-stream")

