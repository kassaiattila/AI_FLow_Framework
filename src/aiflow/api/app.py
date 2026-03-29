"""FastAPI application factory."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
from aiflow._version import __version__

__all__ = ["create_app"]
logger = structlog.get_logger(__name__)

def create_app() -> FastAPI:
    app = FastAPI(
        title="AIFlow API",
        version=__version__,
        description="Enterprise AI Automation Framework",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Include routers
    from aiflow.api.v1.health import router as health_router
    from aiflow.api.v1.workflows import router as workflows_router
    from aiflow.api.v1.chat_completions import router as chat_router
    app.include_router(health_router)
    app.include_router(workflows_router)
    app.include_router(chat_router)
    logger.info("app_created", version=__version__)
    return app
