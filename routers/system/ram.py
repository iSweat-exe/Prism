from fastapi import APIRouter
from fastapi.responses import JSONResponse
import psutil
from services.sampler import sampler

router = APIRouter(
    responses={
        500: {
            "description": "Internal error",
            "content": {
                "application/json": {
                    "example": {
                        "error":   "internal_server_error",
                        "message": "Error details",
                        "path":    "/system/ram",
                    }
                }
            }
        }
    }
)

def get_top_processes() -> list:
    return sampler.get_top_processes()

def get_virtual_memory() -> dict:
    try:
        mem = psutil.virtual_memory()
        return {
            "total_memory":         mem.total,
            "used_memory":          mem.used,
            "free_memory":          mem.free,
            "available_memory":     mem.available,
            "memory_usage_percent": mem.percent,
        }
    except Exception as e:
        raise RuntimeError(f"Unable to retrieve virtual memory: {e}")

def get_swap_memory() -> dict:
    try:
        swap = psutil.swap_memory()
        return {
            "total_swap":         swap.total,
            "used_swap":          swap.used,
            "free_swap":          swap.free,
            "swap_usage_percent": swap.percent,
        }
    except Exception:
        # Swap unavailable, returning neutral values
        return {
            "total_swap":         0,
            "used_swap":          0,
            "free_swap":          0,
            "swap_usage_percent": 0.0,
        }

@router.get("")
def get_ram():
    try:
        return {
            **get_virtual_memory(),
            **get_swap_memory(),
            "top_processes": get_top_processes(),
        }

    except RuntimeError as e:
        return JSONResponse(
            status_code=500,
            content={
                "error":   "ram_data_unavailable",
                "message": str(e),
                "path":    "/system/ram",
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error":   "internal_server_error",
                "message": str(e),
                "path":    "/system/ram",
            }
        )