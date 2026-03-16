# app/api/controllers/report_controller.py
# ─────────────────────────────────────────────────────
# Handles GET /report/{job_id} requests.
# User polls this endpoint until report is ready.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from fastapi import HTTPException, status
from config.logging_config          import get_logger
from shared.types                   import JobId
from shared.types                   import JobStatus
from app.api.models.response_models     import ReportResponse
from app.api.services.job_service       import job_service
from app.api.services.report_service    import report_service

logger = get_logger(__name__)


def handle_get_report(job_id: JobId) -> ReportResponse:
    """
    Handles a report retrieval request.

    Possible responses based on job status:
        QUEUED  → 202 Accepted  — job waiting to start
        RUNNING → 202 Accepted  — pipeline still running
        DONE    → 200 OK        — report ready
        FAILED  → 200 OK        — job failed, error included
        None    → 404 Not Found — job_id doesn't exist

    Args:
        job_id: UUID string from URL path

    Returns:
        ReportResponse with current status and report if ready

    Raises:
        HTTPException 404 if job_id not found
    """
    logger.debug("Report request — job_id=%s", job_id)

    # ── CHECK JOB EXISTS ──────────────────────────────
    job = job_service.get_job(job_id)

    if not job:
        logger.warning("Job not found: %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found. "
                   f"Make sure you submitted a valid job_id.",
        )

    # ── JOB FAILED ────────────────────────────────────
    if job.status == JobStatus.FAILED:
        logger.warning(
            "Job failed: %s error=%s",
            job_id, job.error
        )
        return ReportResponse(
            job_id=job_id,
            status=job.status,
            report=None,
            error=job.error or "Pipeline failed — unknown error",
        )

    # ── JOB DONE — fetch report ───────────────────────
    if job.status == JobStatus.DONE:
        report = report_service.get_report(job_id)

        if not report:
            # Edge case — job marked done but report missing
            logger.error(
                "Job marked done but report missing: %s",
                job_id
            )
            return ReportResponse(
                job_id=job_id,
                status=JobStatus.FAILED,
                report=None,
                error="Report was lost — please resubmit",
            )

        logger.info(
            "Report served: %s length=%d chars",
            job_id, len(report.content)
        )

        return ReportResponse(
            job_id=job_id,
            status=job.status,
            report=report.content,
            error=None,
        )

    # ── STILL RUNNING / QUEUED ────────────────────────
    # Return 202 to tell client to keep polling
    logger.debug(
        "Job still in progress: %s status=%s",
        job_id, job.status
    )

    return ReportResponse(
        job_id=job_id,
        status=job.status,
        report=None,
        error=None,
    )