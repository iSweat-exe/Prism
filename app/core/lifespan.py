from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logger import logger
from app.modules.docker.service import docker_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting PrismAPI...")
    docker_service.init()
    yield
    logger.info("Stopping PrismAPI...")
    await docker_service.close()
