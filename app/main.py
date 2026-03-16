# app/main.py
# ─────────────────────────────────────────────────────
# FastAPI application entry point.
# Creates the app, registers all routers, starts server.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings        import settings
from config.logging_config  import setup_logging, get_logger
from app.api.routes         import analyze_routes, report_routes, health_routes

# Setup logging first — before any other imports use logger
setup_logging()
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application.

    Why a factory function instead of module-level app?
    1. Easier to test — create fresh app per test
    2. Clear initialization order
    3. Standard FastAPI pattern

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Competitor Intelligence Agent API. "
            "Submit a competitor URL and get a full "
            "intelligence report in minutes."
        ),
        docs_url="/docs",
        # Interactive API docs at http://localhost:8000/docs
        redoc_url="/redoc",
    )

    # ── CORS ──────────────────────────────────────────
    # CORS allows the frontend (Streamlit) to call the API
    # Without this, browser blocks cross-origin requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        # "*" = allow all origins — fine for development
        # Production: replace with specific frontend URL
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── REGISTER ROUTERS ──────────────────────────────
    # Each router adds its endpoints to the app
    app.include_router(health_routes.router)
    app.include_router(analyze_routes.router)
    app.include_router(report_routes.router)

    logger.info(
        "%s v%s started",
        settings.APP_NAME,
        settings.APP_VERSION,
    )

    return app


# Create the app instance
# Uvicorn imports this: uvicorn app.main:app
app = create_app()