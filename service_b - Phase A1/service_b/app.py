# service_b/app.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config.settings import settings
from utils.logger import configure_logging, get_logger
from utils.dataset_store import init_dataset_store
from utils.job_store import init_job_store

# Platform routers - DISABLED for V1.5 product boundary
# from routers import preprocessing as preprocessing_router
# from routers import jobs as jobs_router
# from routers import transformation as transformation_router
# from routers import modeling as modeling_router
# from routers import automation as automation_router

# V1.5 product router - ONLY public endpoint
from routers import analyze as analyze_router

# ------------------------------------------------------------------
# Rate Limiter Setup
# ------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, enabled=settings.RATE_LIMIT_ENABLED)

# ------------------------------------------------------------------
# App initialization
# ------------------------------------------------------------------

app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.VERSION,
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
    openapi_tags=[
        {"name": "insights", "description": "Interactive Insight Report Generator endpoints."}
    ],
)

logger = get_logger(__name__)

# ------------------------------------------------------------------
# Rate Limiter State
# ------------------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------

# Security check: Prevent wildcard CORS with credentials in production
if settings.ENVIRONMENT == "production":
    if "*" in settings.CORS_ORIGINS:
        raise RuntimeError(
            "SECURITY ERROR: Wildcard CORS origin ('*') is not allowed in production "
            "when credentials are enabled. Set CORS_ORIGINS to specific origins."
        )
    # Require explicit CORS origins in production
    if not settings.CORS_ORIGINS or settings.CORS_ORIGINS == [""]:
        raise RuntimeError(
            "SECURITY ERROR: CORS_ORIGINS must be explicitly set in production. "
            "Set CORS_ORIGINS environment variable to allowed origins."
        )

cors_origins = ["*"] if settings.ENVIRONMENT == "development" else settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False if settings.ENVIRONMENT == "development" else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------

# V1.5 PRODUCT BOUNDARY: Only analyze endpoint is publicly accessible
# All platform routers are disabled to enforce product scope

# Platform routers - DISABLED (code remains but endpoints are unreachable)
# app.include_router(preprocessing_router.router)
# app.include_router(jobs_router.router)
# app.include_router(transformation_router.router)
# app.include_router(modeling_router.router)
# app.include_router(automation_router.router)

# V1.5 product endpoint - ONLY public API
app.include_router(analyze_router.router, prefix="/v1", tags=["insights"])

# ------------------------------------------------------------------
# Lifecycle events
# ------------------------------------------------------------------

@app.on_event("startup")
async def on_startup() -> None:
    """
    Application startup hook.

    Responsibilities:
    - Configure logging
    - Ensure filesystem layout exists
    - Initialize SQLite-backed stores (dataset + job)
    """
    configure_logging()
    logger.info(
        "Starting service_b application",
        extra={"environment": settings.ENVIRONMENT},
    )

    # Ensure base directories exist (datasets/, logs/, etc.)
    settings.ensure_dirs()

    # IMPORTANT: initialize stores with explicit DB paths
    init_dataset_store(
        db_path=settings.BASE_DATA_PATH / "datasets.sqlite3"
    )
    init_job_store(
        db_path=settings.BASE_DATA_PATH / "jobs.sqlite3"
    )

    logger.info("Startup initialization complete")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """
    Application shutdown hook.

    Currently a placeholder.
    """
    logger.info("Shutting down service_b application")

# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """
    Lightweight health check endpoint.
    """
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
    }


@app.get("/healthz", tags=["health"])
async def healthz() -> dict:
    """
    Standardized health check endpoint.
    """
    return {"status": "ok", "service": "B"}
