"""FastAPI application factory."""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback
import uuid
import structlog
from aiflow._version import __version__

__all__ = ["create_app"]
logger = structlog.get_logger(__name__)

_DEFAULT_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
]


def _get_cors_origins() -> list[str]:
    """Resolve CORS allowed origins from env.

    - AIFLOW_CORS_ORIGINS env var: comma-separated list of origins.
    - Dev/test: falls back to localhost defaults.
    - Production: requires explicit AIFLOW_CORS_ORIGINS.
    """
    raw = os.getenv("AIFLOW_CORS_ORIGINS", "").strip()
    env = os.getenv("AIFLOW_ENVIRONMENT", "dev").lower()
    is_production = env in ("production", "prod")

    if raw:
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        logger.info("cors_origins_configured", origins=origins, env=env)
        return origins

    if is_production:
        raise RuntimeError(
            "AIFLOW_CORS_ORIGINS is REQUIRED in production mode. "
            "Set a comma-separated list of allowed origins."
        )

    logger.warning("cors_using_dev_defaults", origins=_DEFAULT_DEV_ORIGINS, env=env)
    return _DEFAULT_DEV_ORIGINS


def create_app() -> FastAPI:
    # Load .env inside factory (not at module level - avoids test interference)
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup: pool/engine created lazily on first use
        logger.info("app_startup")
        yield
        # Shutdown: close shared DB connections
        from aiflow.api.deps import close_all
        await close_all()
        logger.info("app_shutdown")

    app = FastAPI(
        title="AIFlow API",
        version=__version__,
        description="Enterprise AI Automation Framework",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Auth middleware — enforces Bearer/API key auth on /api/v1/* (after CORS)
    from aiflow.api.middleware import AuthMiddleware
    app.add_middleware(AuthMiddleware)
    # Include routers
    from aiflow.api.v1.health import router as health_router
    from aiflow.api.v1.workflows import router as workflows_router
    from aiflow.api.v1.chat_completions import router as chat_router
    from aiflow.api.v1.feedback import router as feedback_router
    from aiflow.api.v1.runs import router as runs_router
    from aiflow.api.v1.costs import router as costs_router
    from aiflow.api.v1.skills_api import router as skills_router
    from aiflow.api.v1.emails import router as emails_router
    from aiflow.api.v1.auth import router as auth_router
    from aiflow.api.v1.documents import router as documents_router
    from aiflow.api.v1.process_docs import router as process_docs_router
    from aiflow.api.v1.cubix import router as cubix_router
    from aiflow.api.v1.services import router as services_router
    from aiflow.api.v1.rag_engine import router as rag_router
    from aiflow.api.v1.diagram_generator import router as diagram_router
    from aiflow.api.v1.media_processor import router as media_router
    from aiflow.api.v1.rpa_browser import router as rpa_router
    from aiflow.api.v1.human_review import router as review_router
    from aiflow.api.v1.admin import router as admin_router
    from aiflow.api.v1.pipelines import router as pipelines_router
    app.include_router(health_router)
    app.include_router(workflows_router)
    app.include_router(chat_router)
    app.include_router(feedback_router)
    app.include_router(runs_router)
    app.include_router(costs_router)
    app.include_router(skills_router)
    app.include_router(emails_router)
    app.include_router(auth_router)
    app.include_router(documents_router)
    app.include_router(process_docs_router)
    app.include_router(cubix_router)
    app.include_router(services_router)
    app.include_router(rag_router)
    app.include_router(diagram_router)
    app.include_router(media_router)
    app.include_router(rpa_router)
    app.include_router(review_router)
    app.include_router(admin_router)
    app.include_router(pipelines_router)
    # Global exception handler — hides internals in production
    env = os.getenv("AIFLOW_ENVIRONMENT", "dev").lower()
    is_production = env in ("production", "prod")

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        error_id = str(uuid.uuid4())
        tb = traceback.format_exc()
        # Always log full details server-side
        logger.error("unhandled_exception", error_id=error_id, error=str(exc), traceback=tb[:2000])

        if is_production:
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "error_id": error_id},
            )
        # Dev/test: include traceback for debugging
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "error_id": error_id, "traceback": tb[:5000]},
        )

    logger.info("app_created", version=__version__)
    return app
