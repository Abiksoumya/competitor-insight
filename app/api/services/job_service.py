# app/services/job_service.py
# ─────────────────────────────────────────────────────
# Manages job lifecycle — create, update, retrieve.
#
# What is a Service?
# Business logic layer between controllers and DAOs.
# Controllers call services — services call DAOs.
# Services never deal with HTTP (no Request/Response).
# DAOs never deal with business rules (just storage).
#
# Separation:
#   Controller → "handle this HTTP request"
#   Service    → "apply these business rules"
#   DAO        → "read/write this data"
# ─────────────────────────────────────────────────────

from __future__ import annotations
import uuid
from typing import Optional
from datetime import datetime

from app.api.models.domain_models import JobRecord
from config.logging_config    import get_logger
from shared.types             import Url, JobId
from shared.types             import JobStatus
from app.api.dao.job_dao       import job_dao


logger = get_logger(__name__)


class JobService:
    """
    Handles all job lifecycle operations.

    Job lifecycle:
        create()      → status = QUEUED
        mark_running() → status = RUNNING
        mark_done()   → status = DONE
        mark_failed() → status = FAILED
    """

    def create_job(self, url: Url) -> JobRecord:
        """
        Creates a new job record and saves it.
        Called when user submits a URL for analysis.

        Args:
            url: Competitor URL to analyze

        Returns:
            Newly created JobRecord with QUEUED status
        """
        job_id: JobId = str(uuid.uuid4())
        # uuid4() generates a random UUID
        # Example: "3f2a1b9c-bc91-4d8e-a123-456789abcdef"

        job = JobRecord(
            job_id=job_id,
            url=url,
            status=JobStatus.QUEUED,
            created_at=datetime.now(),
            completed_at=None,
            error=None,
        )

        job_dao.save(job)

        logger.info(
            "Job created: %s url=%s",
            job_id, url
        )

        return job

    def get_job(self, job_id: JobId) -> Optional[JobRecord]:
        """
        Retrieves a job by ID.

        Args:
            job_id: UUID string

        Returns:
            JobRecord if found, None if not found
        """
        return job_dao.get(job_id)

    def mark_running(self, job_id: JobId) -> None:
        """
        Updates job status to RUNNING.
        Called when pipeline starts processing.

        Args:
            job_id: UUID string of job to update
        """
        job = job_dao.get(job_id)
        if job:
            job.mark_running()
            job_dao.save(job)
            logger.info("Job running: %s", job_id)

    def mark_done(self, job_id: JobId) -> None:
        """
        Updates job status to DONE.
        Called when pipeline completes successfully.

        Args:
            job_id: UUID string of job to update
        """
        job = job_dao.get(job_id)
        if job:
            job.mark_done()
            job_dao.save(job)
            logger.info("Job done: %s", job_id)

    def mark_failed(self, job_id: JobId, error: str) -> None:
        """
        Updates job status to FAILED with error message.
        Called when pipeline raises an exception.

        Args:
            job_id: UUID string of job to update
            error:  Error message to store
        """
        job = job_dao.get(job_id)
        if job:
            job.mark_failed(error)
            job_dao.save(job)
            logger.error(
                "Job failed: %s error=%s",
                job_id, error
            )

    def job_exists(self, job_id: JobId) -> bool:
        """
        Checks if a job exists.

        Args:
            job_id: UUID string to check

        Returns:
            True if job exists
        """
        return job_dao.exists(job_id)


# Singleton
job_service = JobService()