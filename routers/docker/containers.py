import os

import aiodocker
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from models.schema import ContainerCreate
from services.docker_service import docker_service
from services.logger import logger

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

INTERNAL_CONTAINERS = [
    f"/{os.getenv('APP_NAME', 'prism-api')}",
    f"/{os.getenv('GATEWAY_NAME', 'nginx-proxy')}",
]


def _is_protected(container_info: dict) -> bool:
    """
    Check if a container is protected from destructive operations.
    Protection is based on INTERNAL_CONTAINERS list and 'prism.protected' label.
    """
    name = container_info.get("Name", "")
    labels = container_info.get("Config", {}).get("Labels", {})

    return any(name == ic for ic in INTERNAL_CONTAINERS) or labels.get("prism.protected") == "true"


async def _get_container(container_id: str) -> aiodocker.containers.DockerContainer:
    """
    Helper function to retrieve a Docker container by its ID.
    Handles client initialization check and 404 errors.
    """
    docker = docker_service.client
    if not docker:
        raise HTTPException(status_code=500, detail="Docker client not initialized")
    try:
        return await docker.containers.get(container_id)
    except aiodocker.exceptions.DockerError as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"Container {container_id} not found")
        logger.error(f"Docker error in _get_container: {e}")
        raise HTTPException(status_code=e.status, detail="Docker communication error")


async def list_containers():
    """
    List all containers with basic information using the shared Docker client.
    """
    docker = docker_service.client
    if not docker:
        raise RuntimeError("Docker client not initialized")

    list_data = await docker.containers.list(all=True)
    containers_info = []
    for c in list_data:
        data = c._container
        containers_info.append(
            {
                "id": data.get("Id", "")[:12],
                "full_id": data.get("Id", ""),
                "names": [name.lstrip("/") for name in data.get("Names", [])],
                "image": data.get("Image"),
                "state": data.get("State"),
                "status": data.get("Status"),
                "created": data.get("Created"),
            }
        )
    return containers_info


@router.get("")
async def get_containers():
    """
    Endpoint to list all containers.
    """
    try:
        return await list_containers()
    except Exception as e:
        logger.error(f"Error listing containers: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "docker_list_error",
                "message": "Unable to list containers",
                "path": "/docker/containers",
            },
        )


@router.post("/create")
async def create_container(config: ContainerCreate):
    """
    Endpoint to create and optionally start a new container.
    """
    docker = docker_service.client
    if not docker:
        raise HTTPException(status_code=500, detail="Docker client not initialized")

    # HostConfig transformation for ports and volumes
    host_config = {}

    if config.ports:
        port_bindings = {}
        for container_port, host_port in config.ports.items():
            # Add /tcp if protocol is missing
            if "/" not in container_port:
                container_port = f"{container_port}/tcp"
            port_bindings[container_port] = [{"HostPort": str(host_port)}]
        host_config["PortBindings"] = port_bindings

    if config.volumes:
        host_config["Binds"] = config.volumes

    # Final Docker API configuration
    docker_config = {
        "Image": config.image,
        "Cmd": config.command,
        "Env": config.environment,
        "HostConfig": host_config,
    }

    try:
        try:
            # Try to create the container
            container = await docker.containers.create(config=docker_config, name=config.name)
        except aiodocker.exceptions.DockerError as e:
            # If the image is missing, attempt to pull it automatically
            if e.status == 404 and "No such image" in str(e):
                try:
                    # Note: docker.images.pull handles names
                    # with tags (e.g., "nginx:latest")
                    await docker.images.pull(config.image)
                    # Retry creation after successful pull
                    container = await docker.containers.create(config=docker_config, name=config.name)
                except Exception as pull_err:
                    raise HTTPException(
                        status_code=500,
                        detail=(f"Image {config.image} not found locally and auto-pull failed: {str(pull_err)}"),
                    )
            else:
                logger.error(f"Docker error in create_container: {e}")
                raise HTTPException(status_code=e.status, detail="Docker creation error")

        # After successful creation (or after pull and retry)
        if config.start_after_creation:
            await container.start()

        return {
            "id": container.id,
            "name": config.name or container.id[:12],
            "message": "Container created and started successfully"
            if config.start_after_creation
            else "Container created successfully",
        }
    except HTTPException:
        # Re-raise HTTPExceptions (from our internal handle)
        raise
    except Exception as e:
        logger.error(f"Error creating container: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "docker_create_error",
                "message": "An error occurred during container creation",
                "path": "/docker/containers/create",
            },
        )


@router.get("/{container_id}")
async def get_container_details(container_id: str):
    """
    Endpoint to get detailed information about a container.
    """
    container = await _get_container(container_id)
    try:
        return await container.show()
    except Exception as e:
        logger.error(f"Error inspecting container {container_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "docker_inspect_error",
                "message": "Unable to retrieve container details",
                "path": f"/docker/containers/{container_id}",
            },
        )


@router.post("/{container_id}/start")
async def start_container(container_id: str):
    """
    Endpoint to start a container.
    """
    container = await _get_container(container_id)
    try:
        await container.start()
        return {"message": f"Container {container_id} started successfully"}
    except aiodocker.exceptions.DockerError as e:
        logger.error(f"Error starting container {container_id}: {e}")
        raise HTTPException(status_code=e.status, detail="Docker start error")


@router.post("/{container_id}/stop")
async def stop_container(container_id: str):
    """
    Endpoint to stop a container.
    """
    container = await _get_container(container_id)
    container_info = await container.show()

    if _is_protected(container_info):
        raise HTTPException(
            status_code=403,
            detail="Self-destruction or Gateway interruption is forbidden!",
        )

    try:
        await container.stop()
        return {"message": f"Container {container_id} stopped successfully"}
    except aiodocker.exceptions.DockerError as e:
        logger.error(f"Error stopping container {container_id}: {e}")
        raise HTTPException(status_code=e.status, detail="Docker stop error")


@router.post("/{container_id}/restart")
async def restart_container(container_id: str):
    """
    Endpoint to restart a container.
    """
    container = await _get_container(container_id)
    container_info = await container.show()

    if _is_protected(container_info):
        raise HTTPException(
            status_code=403,
            detail="Self-destruction or Gateway interruption is forbidden!",
        )

    try:
        await container.restart()
        return {"message": f"Container {container_id} restarted successfully"}
    except aiodocker.exceptions.DockerError as e:
        logger.error(f"Error restarting container {container_id}: {e}")
        raise HTTPException(status_code=e.status, detail="Docker restart error")


@router.get("/{container_id}/logs")
async def get_container_logs(container_id: str, tail: int = 100):
    """
    Endpoint to get container logs.
    """
    container = await _get_container(container_id)
    try:
        logs = await container.log(stdout=True, stderr=True, tail=tail)
        return {"logs": logs}
    except aiodocker.exceptions.DockerError as e:
        logger.error(f"Error retrieving logs for {container_id}: {e}")
        raise HTTPException(status_code=e.status, detail="Docker logs error")


@router.delete("/{container_id}")
async def delete_container(container_id: str, force: bool = False, v: bool = False):
    """
    Endpoint to delete a container.
    """
    container = await _get_container(container_id)
    container_info = await container.show()

    if _is_protected(container_info):
        raise HTTPException(
            status_code=403,
            detail="Self-destruction or Gateway destruction is forbidden!",
        )

    try:
        await container.delete(force=force, v=v)
        return {"message": f"Container {container_id} deleted successfully"}
    except aiodocker.exceptions.DockerError as e:
        logger.error(f"Error deleting container {container_id}: {e}")
        raise HTTPException(status_code=e.status, detail="Docker deletion error")


@router.get("/{container_id}/stats")
async def get_container_stats(container_id: str):
    """
    Endpoint to get a snapshot of container statistics.
    """
    container = await _get_container(container_id)
    try:
        # stream=False provides a single snapshot
        stats = await container.stats(stream=False)
        return stats[0] if isinstance(stats, list) and len(stats) > 0 else stats
    except aiodocker.exceptions.DockerError as e:
        logger.error(f"Error retrieving stats for {container_id}: {e}")
        raise HTTPException(status_code=e.status, detail="Docker stats error")
