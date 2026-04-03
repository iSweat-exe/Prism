import json

import aiodocker
from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.exceptions import DockerServiceError, ResourceNotFoundError
from app.core.logger import logger
from app.core.schemas import ImagePullRequest
from app.modules.docker.service import docker_service

router = APIRouter(
    responses={
        500: {
            "description": "Internal error",
            "content": {
                "application/json": {
                    "example": {
                        "error": "internal_server_error",
                        "message": "Error details",
                        "path": "/docker/images",
                    }
                }
            },
        }
    }
)


async def _inspect_image(image_id: str):
    """Helper function to retrieve detailed metadata for a Docker image."""
    docker = docker_service.client
    if not docker:
        raise DockerServiceError("Docker client not initialized", status_code=500)
    try:
        return await docker.images.inspect(image_id)
    except aiodocker.exceptions.DockerError as e:
        if e.status == 404:
            raise ResourceNotFoundError(f"Image {image_id} not found")
        raise DockerServiceError(f"Docker image inspection error: {str(e)}", status_code=e.status)


@router.get("")
async def list_images():
    """Endpoint to list all local Docker images."""
    docker = docker_service.client
    if not docker:
        raise DockerServiceError("Docker client not initialized", status_code=500)
    try:
        images_data = await docker.images.list()
        result = []
        for img in images_data:
            result.append(
                {
                    "id": img["Id"].split(":")[-1][:12] if ":" in img["Id"] else img["Id"][:12],
                    "full_id": img["Id"],
                    "tags": img.get("RepoTags", []),
                    "size": img.get("Size"),
                    "created": img.get("Created"),
                }
            )
        return result
    except Exception as e:
        error_msg = str(e).lower()
        if "cannot connect" in error_msg or "npipe" in error_msg or "docker.sock" in error_msg:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "docker_not_running",
                    "message": "Docker Engine is not started or unreachable.",
                    "path": "/docker/images",
                },
            )
        raise DockerServiceError(f"Unable to list local Docker images: {str(e)}")


@router.get("/{image_id:path}")
async def get_image_details(image_id: str):
    """Endpoint to get detailed information about an image."""
    try:
        return await _inspect_image(image_id)
    except DockerServiceError:
        raise
    except Exception as e:
        raise DockerServiceError(f"Unable to inspect Docker image metadata: {str(e)}")


@router.post("/pull")
async def pull_image(request: ImagePullRequest):
    """Endpoint to pull an image from a registry with real-time progress streaming."""
    docker = docker_service.client
    if not docker:
        raise DockerServiceError("Docker client not initialized", status_code=500)

    async def pull_generator():
        try:
            async for line in docker.images.pull(request.image, stream=True):
                yield json.dumps(line) + "\n"
        except aiodocker.exceptions.DockerError as e:
            logger.error(f"Docker error pulling image {request.image}: {e}")
            yield (json.dumps({"error": "Docker error during image pull", "status": e.status}) + "\n")
        except Exception as e:
            logger.error(f"Unexpected error pulling image {request.image}: {e}")
            yield json.dumps({"error": "Error during image pull orchestration"}) + "\n"

    return StreamingResponse(pull_generator(), media_type="application/x-ndjson")


@router.delete("/{image_id:path}")
async def delete_image(image_id: str, force: bool = False, noprune: bool = False):
    """Endpoint to delete an image."""
    docker = docker_service.client
    if not docker:
        raise DockerServiceError("Docker client not initialized", status_code=500)
    try:
        await docker.images.delete(image_id, force=force, noprune=noprune)
        return {"message": f"Image {image_id} deleted successfully"}
    except aiodocker.exceptions.DockerError as e:
        raise DockerServiceError(f"Docker image deletion error: {str(e)}", status_code=e.status)
    except Exception as e:
        raise DockerServiceError(f"An error occurred while deleting the Docker image: {str(e)}")


@router.post("/prune")
async def prune_images(all_unused: bool = False):
    """Endpoint to prune unused images."""
    docker = docker_service.client
    if not docker:
        raise DockerServiceError("Docker client not initialized", status_code=500)
    try:
        filters = {"dangling": ["false" if all_unused else "true"]}
        result = await docker.images.prune(filters=filters)
        return result
    except aiodocker.exceptions.DockerError as e:
        raise DockerServiceError(f"Docker image prune error: {str(e)}", status_code=e.status)
    except Exception as e:
        raise DockerServiceError(f"Unable to prune unused Docker images: {str(e)}")
