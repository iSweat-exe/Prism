from fastapi import FastAPI

from app.api.v1 import router as v1_router
from app.core.config import settings
from app.core.lifespan import lifespan
from app.core.middleware import setup_middleware

app = FastAPI(
    redirect_slashes=False,
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

setup_middleware(app)

# Global API router including all modules
app.include_router(v1_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8081)
