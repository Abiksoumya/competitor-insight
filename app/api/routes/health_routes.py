# app/api/routes/health_routes.py
# ─────────────────────────────────────────────────────
# GET /health — tells load balancers the app is alive.
# Standard in every production API.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from fastapi import APIRouter
from app.api.models.response_models import HealthResponse
from config.settings import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="Health check",
)
def health() -> HealthResponse:
    """
    GET /health

    Returns:
        { "status": "ok", "version": "1.0.0" }
    """
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
    )