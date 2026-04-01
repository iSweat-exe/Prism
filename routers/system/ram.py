import asyncio
import json

import psutil
from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from services.logger import logger
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
                        "path": "/system/ram",
                    }
                }
            },
        }
    }
)


def get_top_processes() -> list:
    return sampler.get_top_processes()


def get_virtual_memory() -> dict:
    try:
        mem = psutil.virtual_memory()
        return {
            "total_memory": mem.total,
            "used_memory": mem.used,
            "free_memory": mem.free,
            "available_memory": mem.available,
            "memory_usage_percent": mem.percent,
        }
    except Exception as e:
        raise RuntimeError(f"Virtual memory extraction failed: {e}")


def get_swap_memory() -> dict:
    try:
        swap = psutil.swap_memory()
        return {
            "total_swap": swap.total,
            "used_swap": swap.used,
            "free_swap": swap.free,
            "swap_usage_percent": swap.percent,
        }
    except Exception:
        # Swap unavailable, returning neutral values
        return {
            "total_swap": 0,
            "used_swap": 0,
            "free_swap": 0,
            "swap_usage_percent": 0.0,
        }


def fetch_ram_data():
    return {
        **get_virtual_memory(),
        **get_swap_memory(),
        "top_processes": get_top_processes(),
    }


@router.get("")
def get_ram():
    try:
        return fetch_ram_data()

    except RuntimeError as e:
        logger.error(f"Runtime error in get_ram: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "ram_data_unavailable",
                "message": "Unable to retrieve RAM data",
                "path": "/system/ram",
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_ram: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
                "path": "/system/ram",
            },
        )


async def ram_streamer():
    while True:
        try:
            data = fetch_ram_data()
            yield f"data: {json.dumps(data)}\n\n"
        except Exception as e:
            logger.error(f"Error in ram_streamer: {e}")
            yield f"data: {json.dumps({'error': 'stream_interrupted', 'message': 'Unable to stream RAM data'})}\n\n"
        await asyncio.sleep(1)


@router.get("/stream")
async def stream_ram():
    return StreamingResponse(ram_streamer(), media_type="text/event-stream")
