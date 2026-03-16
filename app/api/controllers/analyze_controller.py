

from __future__ import annotations
from fastapi import HTTPException, status
from config.logging_config              import get_logger
from app.api.models.request_models         import AnalyzeRequest
from app.api.models.response_models        import AnalyzeResponse
from app.api.services.job_service          import job_service
from app.api.services.pipeline_service     import pipeline_service

logger = get_logger(__name__)


def handle_analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Handles a competitor analysis request.

    Flow:
        1. Create a new job record
        2. Start pipeline in background thread
        3. Return job_id immediately — don't wait for pipeline

    Args:
        request: Validated AnalyzeRequest with competitor URL

    Returns:
        AnalyzeResponse with job_id and QUEUED status
    """
    url = request.get_url_string()

    logger.info("Analyze request received — url=%s", url)

    try:
        # Step 1 — Create job record
        job = job_service.create_job(url)

        # Step 2 — Start pipeline in background
        # Returns immediately — pipeline runs in separate thread
        pipeline_service.start_pipeline(
            job_id=job.job_id,
            url=url,
        )

        logger.info(
            "Job queued — job_id=%s url=%s",
            job.job_id, url
        )

        # Step 3 — Return response immediately
        return AnalyzeResponse(
            job_id=job.job_id,
            status=job.status,
            message=(
                f"Analysis started for {url}. "
                f"Poll GET /report/{job.job_id} for results."
            ),
        )

    except Exception as e:
        logger.error("Failed to start analysis: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start analysis: {str(e)}",
        )