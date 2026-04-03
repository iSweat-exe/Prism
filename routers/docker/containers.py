import aiodocker
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from models.schema import ContainerCreate
from services.docker_service import docker_service
from services.exceptions import DockerServiceError, ResourceNotFoundError

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


async def _get_container(container_id: str) -> aiodocker.containers.DockerContainer:
    """Helper function to retrieve a Docker container by its ID."""
    docker = docker_service.client
    if not docker:
        raise DockerServiceError("Docker client not initialized", status_code=500)
    try:
        return await docker.containers.get(container_id)
    except aiodocker.exceptions.DockerError as e:
        if e.status == 404:
            raise ResourceNotFoundError(f"Container {container_id} not found")
        raise DockerServiceError(f"Docker communication error: {str(e)}", status_code=e.status)


async def list_containers():
    """List all containers with basic information using the shared Docker client."""
    docker = docker_service.client
    if not docker:
        raise DockerServiceError("Docker client not initialized", status_code=500)

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
    """Endpoint to list all containers."""
    try:
        return await list_containers()
    except DockerServiceError:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "cannot connect" in error_msg or "npipe" in error_msg or "docker.sock" in error_msg:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "docker_not_running",
                    "message": "Docker Engine is not started or unreachable.",
                    "path": "/docker/containers",
                },
            )
        raise DockerServiceError(f"Unable to list containers: {str(e)}")


@router.post("/create")
async def create_container(config: ContainerCreate):
    """Endpoint to create and optionally start a new container."""
    docker = docker_service.client
    if not docker:
        raise DockerServiceError("Docker client not initialized", status_code=500)

    # HostConfig transformation for ports and volumes
    host_config = {}

    if config.ports:
        port_bindings = {}
        for container_port, host_port in config.ports.items():
            if "/" not in container_port:
                container_port = f"{container_port}/tcp"
            port_bindings[container_port] = [{"HostPort": str(host_port)}]
        host_config["PortBindings"] = port_bindings

    if config.volumes:
        host_config["Binds"] = config.volumes

    docker_config = {
        "Image": config.image,
        "Cmd": config.command,
        "Env": config.environment,
        "HostConfig": host_config,
    }

    try:
        try:
            container = await docker.containers.create(config=docker_config, name=config.name)
        except aiodocker.exceptions.DockerError as e:
            if e.status == 404 and "No such image" in str(e):
                try:
                    await docker.images.pull(config.image)
                    container = await docker.containers.create(config=docker_config, name=config.name)
                except Exception as ex:
                    raise DockerServiceError(f"Image {config.image} not found and automatic pull failed: {str(ex)}")
            else:
                raise DockerServiceError(f"Docker creation error: {str(e)}", status_code=e.status)

        if config.start_after_creation:
            await container.start()

        return {
            "id": container.id,
            "name": config.name or container.id[:12],
            "message": "Container created and started successfully"
            if config.start_after_creation
            else "Container created successfully",
        }
    except DockerServiceError:
        raise
    except Exception as e:
        raise DockerServiceError(f"An error occurred during container creation: {str(e)}")


@router.get("/{container_id}")
async def get_container_details(container_id: str):
    """Endpoint to get detailed information about a container."""
    container = await _get_container(container_id)
    try:
        return await container.show()
    except Exception as e:
        raise DockerServiceError(f"Unable to retrieve container details: {str(e)}")


@router.post("/{container_id}/start")
async def start_container(container_id: str):
    """Endpoint to start a container."""
    container = await _get_container(container_id)
    try:
        await container.start()
        return {"message": f"Container {container_id} started successfully"}
    except aiodocker.exceptions.DockerError as e:
        raise DockerServiceError(f"Docker start error: {str(e)}", status_code=e.status)


@router.post("/{container_id}/stop")
async def stop_container(container_id: str):
    """Endpoint to stop a container."""
    container = await _get_container(container_id)
    try:
        await container.stop()
        return {"message": f"Container {container_id} stopped successfully"}
    except aiodocker.exceptions.DockerError as e:
        raise DockerServiceError(f"Docker stop error: {str(e)}", status_code=e.status)


@router.post("/{container_id}/restart")
async def restart_container(container_id: str):
    """Endpoint to restart a container."""
    container = await _get_container(container_id)
    try:
        await container.restart()
        return {"message": f"Container {container_id} restarted successfully"}
    except aiodocker.exceptions.DockerError as e:
        raise DockerServiceError(f"Docker restart error: {str(e)}", status_code=e.status)


@router.get("/{container_id}/logs")
async def get_container_logs(container_id: str, tail: int = 100):
    """Endpoint to get container logs."""
    container = await _get_container(container_id)
    try:
        logs = await container.log(stdout=True, stderr=True, tail=tail)
        return {"logs": logs}
    except aiodocker.exceptions.DockerError as e:
        raise DockerServiceError(f"Docker logs error: {str(e)}", status_code=e.status)


@router.delete("/{container_id}")
async def delete_container(container_id: str, force: bool = False, v: bool = False):
    """Endpoint to delete a container."""
    container = await _get_container(container_id)
    try:
        await container.delete(force=force, v=v)
        return {"message": f"Container {container_id} deleted successfully"}
    except aiodocker.exceptions.DockerError as e:
        raise DockerServiceError(f"Docker deletion error: {str(e)}", status_code=e.status)


@router.get("/{container_id}/stats")
async def get_container_stats(container_id: str):
    """Endpoint to get a snapshot of container statistics."""
    container = await _get_container(container_id)
    try:
        stats = await container.stats(stream=False)
        return stats[0] if isinstance(stats, list) and len(stats) > 0 else stats
    except aiodocker.exceptions.DockerError as e:
        raise DockerServiceError(f"Docker stats error: {str(e)}", status_code=e.status)
