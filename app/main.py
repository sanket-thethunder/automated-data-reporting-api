"""
Automated Report Generator — FastAPI Application Entry Point

Initialises the FastAPI app, registers routers, configures middleware,
and sets up startup/shutdown lifecycle hooks.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import upload, report, summary
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    logger.info("🚀 Report Generator API starting up...")
    yield
    logger.info("🛑 Report Generator API shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A REST API that ingests raw CSV / JSON data, computes summary statistics, "
        "and generates downloadable PDF or Excel reports automatically."
    ),
    version=settings.APP_VERSION,
    contact={
        "name": "Report Generator",
        "url": "https://github.com/yourusername/report-generator",
    },
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

register_exception_handlers(app)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(summary.router, prefix="/summary", tags=["Summary"])
app.include_router(report.router, prefix="/report", tags=["Report"])


# ---------------------------------------------------------------------------
# Health-check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Return a simple liveness probe response."""
    return {"status": "ok", "version": settings.APP_VERSION}
