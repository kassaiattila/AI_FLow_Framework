"""FastAPI application factory."""

import os
import traceback
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

        # Initialize Langfuse tracer (global singleton)
        langfuse_tracer = None
        try:
            from aiflow.observability.tracing import LangfuseTracer
            from aiflow.security.resolver import get_secret_manager

            mgr = get_secret_manager()
            pk = (
                mgr.get_secret("langfuse#public_key", env_alias="AIFLOW_LANGFUSE__PUBLIC_KEY") or ""
            )
            sk = (
                mgr.get_secret("langfuse#secret_key", env_alias="AIFLOW_LANGFUSE__SECRET_KEY") or ""
            )
            host = os.getenv("AIFLOW_LANGFUSE__HOST", "https://cloud.langfuse.com")
            enabled = os.getenv("AIFLOW_LANGFUSE__ENABLED", "false").lower() in ("true", "1", "yes")
            if pk and sk:
                langfuse_tracer = LangfuseTracer(
                    public_key=pk,
                    secret_key=sk,
                    host=host,
                    enabled=enabled,
                )
                app.state.langfuse_tracer = langfuse_tracer
        except Exception as exc:
            logger.warning("langfuse_init_skipped", error=str(exc))

        yield

        # Shutdown: flush Langfuse and close shared DB connections
        if langfuse_tracer:
            langfuse_tracer.shutdown()
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
    cors_origins = _get_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=bool(cors_origins),
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "Accept",
            "Accept-Language",
        ],
    )
    # Security middleware stack (outermost runs first)
    from aiflow.api.middleware import (
        AuthMiddleware,
        MaxBodySizeMiddleware,
        RateLimitMiddleware,
        SecurityHeadersMiddleware,
    )

    # Order: SecurityHeaders wraps everything, then MaxBodySize, then RateLimit, then Auth
    app.add_middleware(AuthMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(MaxBodySizeMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    # Include routers
    from aiflow.api.v1.admin import router as admin_router
    from aiflow.api.v1.auth import router as auth_router
    from aiflow.api.v1.chat_completions import router as chat_router
    from aiflow.api.v1.costs import router as costs_router
    from aiflow.api.v1.cubix import router as cubix_router
    from aiflow.api.v1.data_router import router as data_router_router
    from aiflow.api.v1.diagram_generator import router as diagram_router
    from aiflow.api.v1.document_extractor import router as document_extractor_router
    from aiflow.api.v1.documents import router as documents_router
    from aiflow.api.v1.emails import router as emails_router
    from aiflow.api.v1.feedback import router as feedback_router
    from aiflow.api.v1.health import router as health_router
    from aiflow.api.v1.human_review import router as review_router
    from aiflow.api.v1.intake import router as intake_router
    from aiflow.api.v1.intent_schemas import router as intent_schemas_router
    from aiflow.api.v1.media_processor import router as media_router
    from aiflow.api.v1.monitoring import router as monitoring_router
    from aiflow.api.v1.notifications import router as notifications_router
    from aiflow.api.v1.pipelines import router as pipelines_router
    from aiflow.api.v1.process_docs import router as process_docs_router
    from aiflow.api.v1.prompt_workflows import router as prompt_workflows_router
    from aiflow.api.v1.prompts import router as prompts_router
    from aiflow.api.v1.quality import router as quality_router
    from aiflow.api.v1.rag_advanced import router as rag_advanced_router
    from aiflow.api.v1.rag_collections import router as rag_collections_router
    from aiflow.api.v1.rag_engine import router as rag_router
    from aiflow.api.v1.rpa_browser import router as rpa_router
    from aiflow.api.v1.runs import router as runs_router
    from aiflow.api.v1.services import router as services_router
    from aiflow.api.v1.skills_api import router as skills_router
    from aiflow.api.v1.sources_webhook import router as sources_webhook_router
    from aiflow.api.v1.spec_writer import router as spec_writer_router
    from aiflow.api.v1.tenant_budgets import router as tenant_budgets_router
    from aiflow.api.v1.verifications import router as verifications_router

    app.include_router(health_router)
    app.include_router(sources_webhook_router)
    app.include_router(intake_router)
    app.include_router(chat_router)
    app.include_router(feedback_router)
    app.include_router(runs_router)
    app.include_router(costs_router)
    app.include_router(tenant_budgets_router)
    app.include_router(skills_router)
    app.include_router(emails_router)
    app.include_router(auth_router)
    app.include_router(verifications_router)  # before documents (has /:path catch-all)
    app.include_router(documents_router)
    app.include_router(document_extractor_router)
    app.include_router(process_docs_router)
    app.include_router(cubix_router)
    app.include_router(services_router)
    app.include_router(rag_router)
    app.include_router(diagram_router)
    app.include_router(spec_writer_router)
    app.include_router(media_router)
    app.include_router(rpa_router)
    app.include_router(review_router)
    app.include_router(admin_router)
    app.include_router(monitoring_router)
    app.include_router(pipelines_router)
    app.include_router(notifications_router)
    app.include_router(data_router_router)
    app.include_router(rag_advanced_router)
    app.include_router(rag_collections_router)
    app.include_router(quality_router)
    app.include_router(intent_schemas_router)
    # IMPORTANT: workflow router must be mounted BEFORE the prompts router —
    # the latter has a `/{prompt_name:path}` catch-all that would shadow
    # `/api/v1/prompts/workflows*` otherwise.
    app.include_router(prompt_workflows_router)
    app.include_router(prompts_router)
    # Global exception handler — hides internals in production
    env = os.getenv("AIFLOW_ENVIRONMENT", "dev").lower()
    is_production = env in ("production", "prod")

    from aiflow.core.errors import CostCapBreached, CostGuardrailRefused

    @app.exception_handler(CostCapBreached)
    async def cost_cap_breached_handler(request: Request, exc: CostCapBreached):
        logger.warning(
            "cost_cap_breached",
            tenant_id=exc.tenant_id,
            cap_usd=exc.cap_usd,
            current_usd=exc.current_usd,
            window_h=exc.window_h,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "detail": exc.message,
                "error_code": exc.error_code,
                "tenant_id": exc.tenant_id,
                "cap_usd": exc.cap_usd,
                "current_usd": exc.current_usd,
                "window_h": exc.window_h,
            },
        )

    @app.exception_handler(CostGuardrailRefused)
    async def cost_guardrail_refused_handler(request: Request, exc: CostGuardrailRefused):
        logger.warning(
            "cost_guardrail_refused",
            tenant_id=exc.tenant_id,
            projected_usd=exc.projected_usd,
            remaining_usd=exc.remaining_usd,
            period=exc.period,
            reason=exc.reason,
            dry_run=exc.dry_run,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "detail": exc.message,
                "error_code": exc.error_code,
                **exc.details,
            },
        )

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
