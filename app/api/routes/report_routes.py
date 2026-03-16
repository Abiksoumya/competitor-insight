# app/api/routes/report_routes.py
# ─────────────────────────────────────────────────────
# Defines the GET /report/{job_id} endpoint.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from fastapi import APIRouter
from app.api.controllers.report_controller  import handle_get_report
from app.api.models.response_models import ReportResponse

router = APIRouter(prefix="/report", tags=["Reports"])


@router.get(
    "/{job_id}",
    response_model=ReportResponse,
    summary="Get analysis report",
    description=(
        "Poll this endpoint after submitting a URL for analysis. "
        "Returns status=queued or running while in progress. "
        "Returns status=done with the full report when complete. "
        "Returns status=failed with error if something went wrong."
    ),
)
def get_report(job_id: str) -> ReportResponse:
    """
    GET /report/{job_id}

    Returns:
        While running: { "job_id": "...", "status": "running" }
        When done:     { "job_id": "...", "status": "done", "report": "..." }
        If failed:     { "job_id": "...", "status": "failed", "error": "..." }
    """
    return handle_get_report(job_id)