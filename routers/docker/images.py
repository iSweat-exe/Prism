import json

import aiodocker
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from services.logger import logger

from models.schema import ImagePullRequest
from services.docker_service import docker_service

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
    """
    Helper function to retrieve detailed metadata for a Docker image.
    Returns a dictionary of information.
    """
    docker = docker_service.client
    if not docker:
        raise HTTPException(status_code=500, detail="Docker client not initialized")
    try:
        # aiodocker.images.inspect() returns a dictionary of image details
        return await docker.images.inspect(image_id)
    except aiodocker.exceptions.DockerError as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"Image {image_id} not found")
        raise HTTPException(status_code=e.status, detail="Docker image inspection error")


@router.get("")
async def list_images():
    """
    Endpoint to list all local Docker images.
    """
    docker = docker_service.client
    if not docker:
        raise HTTPException(status_code=500, detail="Docker client not initialized")
    try:
        # aiodocker.images.list() returns a list of dictionaries
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
            
        logger.error(f"Error listing images: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "docker_list_images_error",
                "message": "Unable to list local Docker images",
                "path": "/docker/images",
            },
        )


@router.get("/{image_id:path}")
async def get_image_details(image_id: str):
    """
    Endpoint to get detailed information about an image.
    Uses 'path' converter to support tags with colons (e.g., nginx:latest).
    """
    try:
        return await _inspect_image(image_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error inspecting image {image_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "docker_inspect_image_error",
                "message": "Unable to inspect Docker image metadata",
                "path": f"/docker/images/{image_id}",
            },
        )


@router.post("/pull")
async def pull_image(request: ImagePullRequest):
    """
    Endpoint to pull an image from a registry with real-time progress streaming.
    """
    docker = docker_service.client
    if not docker:
        raise HTTPException(status_code=500, detail="Docker client not initialized")

    async def pull_generator():
        try:
            # stream=True returns an async generator yielding progress dicts
            async for line in docker.images.pull(request.image, stream=True):
                yield json.dumps(line) + "\n"
        except aiodocker.exceptions.DockerError as e:
            logger.error(f"Docker error pulling image {request.image}: {e}")
            yield json.dumps(
                {
                    "error": "Docker error during image pull",
                    "status": e.status,
                }
            ) + "\n"
        except Exception as e:
            logger.error(f"Unexpected error pulling image {request.image}: {e}")
            yield json.dumps({"error": "Error during image pull orchestration"}) + "\n"

    return StreamingResponse(pull_generator(), media_type="application/x-ndjson")


@router.delete("/{image_id:path}")
async def delete_image(image_id: str, force: bool = False, noprune: bool = False):
    """
    Endpoint to delete an image.
    Uses 'path' converter to support tags with colons.
    """
    docker = docker_service.client
    if not docker:
        raise HTTPException(status_code=500, detail="Docker client not initialized")
    try:
        # aiodocker.images.delete()
        await docker.images.delete(image_id, force=force, noprune=noprune)
        return {"message": f"Image {image_id} deleted successfully"}
    except aiodocker.exceptions.DockerError as e:
        raise HTTPException(status_code=e.status, detail="Docker image deletion error")
    except Exception as e:
        logger.error(f"Error deleting image {image_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "docker_delete_image_error",
                "message": "An error occurred while deleting the Docker image",
                "path": f"/docker/images/{image_id}",
            },
        )


@router.post("/prune")
async def prune_images(all_unused: bool = False):
    """
    Endpoint to prune unused images.
    If all_unused is True, it prunes all unused images, not just dangling ones.
    """
    docker = docker_service.client
    if not docker:
        raise HTTPException(status_code=500, detail="Docker client not initialized")
    try:
        # dangling='false' prunes all unused images (like docker image prune -a)
        filters = {"dangling": ["false" if all_unused else "true"]}
        result = await docker.images.prune(filters=filters)
        return result
    except aiodocker.exceptions.DockerError as e:
        raise HTTPException(status_code=e.status, detail="Docker image prune error")
    except Exception as e:
        logger.error(f"Error pruning images: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "docker_prune_images_error",
                "message": "Unable to prune unused Docker images",
                "path": "/docker/images/prune",
            },
        )
