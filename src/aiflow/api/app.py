"""FastAPI application factory."""
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import traceback
from aiflow._version import __version__

__all__ = ["create_app"]
logger = structlog.get_logger(__name__)

def create_app() -> FastAPI:
    # Load .env inside factory (not at module level - avoids test interference)
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

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
    # Global exception handler for debugging
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        tb = traceback.format_exc()
        logger.error("unhandled_exception", error=str(exc), traceback=tb[:500])
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "traceback": tb[:1000]},
        )

    logger.info("app_created", version=__version__)
    return app
