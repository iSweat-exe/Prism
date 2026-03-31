from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import aiodocker

router = APIRouter(
    responses={
        500: {
            "description": "Internal error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "internal_server_error",
                        "message": "Error details",
                        "path": "/docker/containers",
                    }
                }
            },
        }
    }
)


async def list_containers():
    """
    List all containers with basic information.
    """
    docker = aiodocker.Docker()
    try:
        # containers.list() returns a list of dictionaries with basic info
        list_data = await docker.containers.list(all=True)
        containers_info = []
        for c in list_data:
            # c is a DockerContainer object, its raw data is in c._container
            data = c._container
            containers_info.append({
                "id": data.get("Id", "")[:12],
                "full_id": data.get("Id", ""),
                "names": [name.lstrip("/") for name in data.get("Names", [])],
                "image": data.get("Image"),
                "state": data.get("State"),
                "status": data.get("Status"),
                "created": data.get("Created"),
            })
        return containers_info
    finally:
        await docker.close()


@router.get("")
async def get_containers():
    """
    Endpoint to list all containers.
    """
    try:
        return await list_containers()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "docker_list_error",
                "message": str(e),
                "path": "/docker/containers",
            },
        )


@router.get("/{container_id}")
async def get_container_details(container_id: str):
    """
    Endpoint to get detailed information about a container.
    """
    docker = aiodocker.Docker()
    try:
        container = await docker.containers.get(container_id)
        return await container.show()
    except aiodocker.exceptions.DockerError as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail="Container not found")
        raise HTTPException(status_code=e.status, detail=str(e))
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "docker_inspect_error",
                "message": str(e),
                "path": f"/docker/containers/{container_id}",
            },
        )
    finally:
        await docker.close()


@router.post("/{container_id}/start")
async def start_container(container_id: str):
    """
    Endpoint to start a container.
    """
    docker = aiodocker.Docker()
    try:
        container = await docker.containers.get(container_id)
        await container.start()
        return {"message": "Container started successfully"}
    except aiodocker.exceptions.DockerError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    finally:
        await docker.close()


@router.post("/{container_id}/stop")
async def stop_container(container_id: str):
    """
    Endpoint to stop a container.
    """
    docker = aiodocker.Docker()
    try:
        container = await docker.containers.get(container_id)
        await container.stop()
        return {"message": "Container stopped successfully"}
    except aiodocker.exceptions.DockerError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    finally:
        await docker.close()


@router.post("/{container_id}/restart")
async def restart_container(container_id: str):
    """
    Endpoint to restart a container.
    """
    docker = aiodocker.Docker()
    try:
        container = await docker.containers.get(container_id)
        await container.restart()
        return {"message": "Container restarted successfully"}
    except aiodocker.exceptions.DockerError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    finally:
        await docker.close()


@router.get("/{container_id}/logs")
async def get_container_logs(container_id: str, tail: int = 100):
    """
    Endpoint to get container logs.
    """
    docker = aiodocker.Docker()
    try:
        container = await docker.containers.get(container_id)
        logs = await container.log(stdout=True, stderr=True, tail=tail)
        return {"logs": logs}
    except aiodocker.exceptions.DockerError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    finally:
        await docker.close()


@router.delete("/{container_id}")
async def delete_container(container_id: str, force: bool = False, v: bool = False):
    """
    Endpoint to delete a container.
    """
    docker = aiodocker.Docker()
    try:
        container = await docker.containers.get(container_id)
        await container.delete(force=force, v=v)
        return {"message": f"Container {container_id} deleted successfully"}
    except aiodocker.exceptions.DockerError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    finally:
        await docker.close()


@router.get("/{container_id}/stats")
async def get_container_stats(container_id: str):
    """
    Endpoint to get a snapshot of container statistics.
    """
    docker = aiodocker.Docker()
    try:
        container = await docker.containers.get(container_id)
        # stream=False provides a single snapshot
        stats = await container.stats(stream=False)
        # Ensure we return a single dict, not a list with one dict
        return stats[0] if isinstance(stats, list) and len(stats) > 0 else stats
    except aiodocker.exceptions.DockerError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    finally:
        await docker.close()
