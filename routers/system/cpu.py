from fastapi import APIRouter
from fastapi.responses import JSONResponse
import psutil
import platform
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
                        "path":    "/system/cpu",
                    }
                }
            }
        }
    }
)

def get_cpu_brand() -> str:
    return sampler.get_cpu_metadata()["brand"]

def get_vendor_id() -> str:
    return sampler.get_cpu_metadata()["vendor_id"]

def get_temperatures() -> list:
    try:
        sensors = psutil.sensors_temperatures()
        if not sensors:
            return []
        return [
            {"label": entry.label or name, "current": entry.current}
            for name, entries in sensors.items()
            for entry in entries
        ]
    except AttributeError:
        return []  # Unsupported on Windows
    except Exception:
        return []

@router.get("")
def get_cpu():
    try:
        freq      = psutil.cpu_freq(percpu=False)
        freqs     = psutil.cpu_freq(percpu=True) or []
        usages    = sampler.get_cpu_usage()
        brand     = get_cpu_brand()
        vendor_id = get_vendor_id()

        if not freq:
            raise RuntimeError("Unable to retrieve CPU frequency")

        if not usages:
            raise RuntimeError("Unable to retrieve CPU usage")

        cores = [
            {
                "index":     i,
                "name":      f"CPU {i + 1}",
                "usage":     usages[i],
                "frequency": int(freqs[i].current) if i < len(freqs) else int(freq.current),
                "brand":     brand,
                "vendor_id": vendor_id,
            }
            for i in range(len(usages))
        ]

        return {
            "global": {
                "usage":          round(sum(usages) / len(usages), 2),
                "logical_cores":  psutil.cpu_count(logical=True),
                "physical_cores": psutil.cpu_count(logical=False),
                "avg_frequency":  int(freq.current),
                "min_frequency":  int(freq.min),
                "max_frequency":  int(freq.max),
                "arch":           platform.machine(),
                "brand":          brand,
                "vendor_id":      vendor_id,
            },
            "cores":        cores,
            "temperatures": get_temperatures(),
        }

    except RuntimeError as e:
        return JSONResponse(
            status_code=500,
            content={
                "error":   "cpu_data_unavailable",
                "message": str(e),
                "path":    "/system/cpu",
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error":   "internal_server_error",
                "message": str(e),
                "path":    "/system/cpu",
            }
        )