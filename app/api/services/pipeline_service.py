

from __future__ import annotations
import threading

from config.logging_config       import get_logger
from shared.types                import JobId, Url
from pipeline.graph              import run_pipeline
from app.api.services.job_service    import job_service
from app.api.services.report_service import report_service

logger = get_logger(__name__)


def _run_pipeline_background(job_id: JobId, url: Url) -> None:
    """
    Runs the full pipeline in a background thread.
    This function is what the thread actually executes.

    Flow:
        1. Mark job as RUNNING
        2. Run the LangGraph pipeline
        3. Save the report
        4. Mark job as DONE
        If anything fails → mark job as FAILED

    Args:
        job_id: UUID of the job to process
        url:    Competitor URL to analyze
    """
    logger.info(
        "Background pipeline starting — job_id=%s url=%s",
        job_id, url
    )

    try:
        # ── STEP 1: Mark job as running ───────────────
        job_service.mark_running(job_id)

        # ── STEP 2: Run the pipeline ──────────────────
        # This blocks the background thread for 3-5 minutes
        # while all agents do their work
        report_content = run_pipeline(url)

        # ── STEP 3: Save the report ───────────────────
        report_service.save_report(
            job_id=job_id,
            url=url,
            content=report_content,
        )

        # ── STEP 4: Mark job as done ──────────────────
        job_service.mark_done(job_id)

        logger.info(
            "Background pipeline complete — job_id=%s",
            job_id
        )

    except Exception as e:
        # Pipeline failed — mark job as failed with error
        error_msg = str(e)
        logger.error(
            "Background pipeline failed — job_id=%s error=%s",
            job_id, error_msg
        )
        job_service.mark_failed(job_id, error_msg)


class PipelineService:
    """
    Manages background pipeline execution.
    Provides a clean interface for controllers to start jobs.
    """

    def start_pipeline(self, job_id: JobId, url: Url) -> None:
        """
        Starts the pipeline in a background thread.
        Returns immediately — pipeline runs in background.

        Why threading.Thread instead of asyncio?
        FastAPI supports async but our pipeline uses
        synchronous CrewAI and LangGraph calls.
        threading.Thread is the simplest way to run
        blocking code in the background without blocking
        the FastAPI event loop.

        Args:
            job_id: UUID of the job to process
            url:    Competitor URL to analyze
        """
        thread = threading.Thread(
            target=_run_pipeline_background,
            args=(job_id, url),
            # daemon=True means thread dies when main app dies
            # Prevents zombie threads if app shuts down
            daemon=True,
            name=f"pipeline-{job_id[:8]}",
            # Short name for easier debugging in thread dumps
        )

        thread.start()

        logger.info(
            "Pipeline thread started — job_id=%s thread=%s",
            job_id, thread.name
        )


# Singleton
pipeline_service = PipelineService()