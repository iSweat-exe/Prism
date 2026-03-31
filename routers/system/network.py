from fastapi import APIRouter
from fastapi.responses import JSONResponse
import psutil
import socket
import time
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
                        "path":    "/system/network",
                    }
                }
            }
        }
    }
)

def build_interfaces(addrs: dict, net_cache: dict) -> list:
    af_link = psutil.AF_LINK
    interfaces = []

    for name, stats in net_cache.items():
        try:
            mac_address = "00:00:00:00:00:00"
            ip_networks = []

            for addr in addrs.get(name, []):
                if addr.family == af_link:
                    mac_address = addr.address
                elif addr.family == socket.AF_INET:
                    prefix = sum(bin(int(x)).count("1") for x in addr.netmask.split(".")) if addr.netmask else 24
                    ip_networks.append({"addr": addr.address, "prefix": prefix})
                elif addr.family == socket.AF_INET6:
                    prefix = int(addr.netmask.split("/")[-1]) if addr.netmask and "/" in addr.netmask else 64
                    ip_networks.append({"addr": addr.address, "prefix": prefix})

            recv = stats["received"]
            sent = stats["transmitted"]

            interfaces.append({
                "name":               name,
                "mac_address":        mac_address,
                "mtu":                1500,
                "ip_networks":        ip_networks,
                "received":           recv,
                "transmitted":        sent,
                "received_mbps":      round(recv / 1_000_000, 6),
                "transmitted_mbps":   round(sent / 1_000_000, 6),
                **{k: stats[k] for k in [
                    "total_received", "total_transmitted",
                    "packets_received", "packets_transmitted",
                    "total_packets_received", "total_packets_transmitted",
                    "errors_on_received", "errors_on_transmitted",
                    "total_errors_on_received", "total_errors_on_transmitted",
                ]}
            })

        except Exception:
            pass  # An interface in error does not block others

    return interfaces

@router.get("")
def get_network():
    try:
        net_cache, sample_error = sampler.get_net_cache()
        
        # If the sampling thread is in error, bubble it up
        if sample_error:
            raise RuntimeError(sample_error)

        if not net_cache:
            raise RuntimeError("Network cache empty, sampler starting...")

        addrs      = psutil.net_if_addrs()
        interfaces = build_interfaces(addrs, net_cache)

        return {
            "global":     {"latency_ms": sampler.get_latency()},
            "interfaces": interfaces,
        }

    except RuntimeError as e:
        return JSONResponse(
            status_code=500,
            content={
                "error":   "network_data_unavailable",
                "message": str(e),
                "path":    "/system/network",
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error":   "internal_server_error",
                "message": str(e),
                "path":    "/system/network",
            }
        )