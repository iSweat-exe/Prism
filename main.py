from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.api import api_info
from routers.system import cpu, ram, disk, network, os, uptime

app = FastAPI(redirect_slashes=False, title="PrismAPI", version="1.0.0")

#! EDIT BEFORE PRODUCTION
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/system")
def get_system():
    return {
        "api": api_info(),
        "os": os.get_os(),
        "uptime": uptime.get_uptime(),
        "cpu": cpu.get_cpu(),
        "ram": ram.get_ram(),
        "disk": disk.get_disk(),
        "network": network.get_network(),
    }


app.include_router(cpu.router, prefix="/system/cpu", tags=["System Cpu"])
app.include_router(ram.router, prefix="/system/ram", tags=["System Ram"])
app.include_router(disk.router, prefix="/system/disk", tags=["System Disk"])
app.include_router(network.router, prefix="/system/network", tags=["System Network"])
app.include_router(os.router, prefix="/system/os", tags=["System Os"])
app.include_router(uptime.router, prefix="/system/uptime", tags=["System Uptime"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8081)
