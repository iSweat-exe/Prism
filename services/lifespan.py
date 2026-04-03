from contextlib import asynccontextmanager

from fastapi import FastAPI

from .docker_service import docker_service
from .logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting PrismAPI...")
    docker_service.init()
    yield
    logger.info("Stopping PrismAPI...")
    await docker_service.close()
