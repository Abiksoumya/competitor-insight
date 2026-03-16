# app/api/routes/analyze_routes.py
# ─────────────────────────────────────────────────────
# Defines the POST /analyze endpoint.
#
# What does a route do?
# - Defines the URL path and HTTP method
# - Declares request and response types
# - Calls the controller — nothing else
#
# Routes are intentionally thin — all logic in controller.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from fastapi import APIRouter

from app.api.controllers.analyze_controller import handle_analyze
from app.api.models.request_models import AnalyzeRequest
from app.api.models.response_models import AnalyzeResponse

# APIRouter groups related endpoints together
# prefix="/analyze" means all routes here start with /analyze
router = APIRouter(prefix="/analyze", tags=["Analysis"])


@router.post(
    "",
    response_model=AnalyzeResponse,
    status_code=202,
    summary="Start competitor analysis",
    description=(
        "Submit a competitor URL to start analysis. "
        "Returns a job_id immediately. "
        "Poll GET /report/{job_id} for the completed report."
    ),
)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    POST /analyze

    Body:
        { "url": "https://competitor.com" }

    Returns:
        { "job_id": "uuid", "status": "queued", "message": "..." }
    """
    return handle_analyze(request)