

from __future__ import annotations
from typing import Optional
from app.api.models.domain_models import JobRecord
from config.logging_config import get_logger

logger = get_logger(__name__)


class JobDAO:
    """
    In-memory storage for pipeline jobs.

    Why a class instead of module-level dict?
    1. Encapsulation — storage is private (_jobs)
    2. Easy to mock in tests — inject a fake JobDAO
    3. Clean interface — callers use methods, not dict ops
    4. Future-proof — swap dict for DB without changing callers

    Storage:
        _jobs: dict[job_id, JobRecord]
        key   = job_id string
        value = JobRecord dataclass
    """

    def __init__(self) -> None:
        # Private dict — only accessible through methods
        # job_id → JobRecord
        self._jobs: dict[str, JobRecord] = {}
        logger.debug("JobDAO initialized")

    def save(self, job: JobRecord) -> None:
        """
        Saves or updates a job record.
        Called when job is created, started, completed, or failed.

        Args:
            job: JobRecord to save
        """
        self._jobs[job.job_id] = job
        logger.debug("Job saved: %s status=%s", job.job_id, job.status)

    def get(self, job_id: str) -> Optional[JobRecord]:
        """
        Retrieves a job by ID.
        Returns None if job does not exist.

        Args:
            job_id: UUID string identifying the job

        Returns:
            JobRecord if found, None if not found
        """
        job = self._jobs.get(job_id)
        if not job:
            logger.debug("Job not found: %s", job_id)
        return job

    def exists(self, job_id: str) -> bool:
        """
        Checks if a job exists without returning the full record.
        Faster than get() when you only need existence check.

        Args:
            job_id: UUID string to check

        Returns:
            True if job exists, False otherwise
        """
        return job_id in self._jobs

    def get_all(self) -> list[JobRecord]:
        """
        Returns all jobs sorted by creation time (newest first).
        Used for admin/debug endpoints.

        Returns:
            List of all JobRecord objects
        """
        return sorted(
            self._jobs.values(),
            key=lambda j: j.created_at,
            reverse=True,
        )

    def count(self) -> int:
        """Returns total number of jobs stored."""
        return len(self._jobs)

    def delete(self, job_id: str) -> bool:
        """
        Deletes a job record.
        Returns True if deleted, False if not found.

        Args:
            job_id: UUID string to delete

        Returns:
            True if job was deleted, False if not found
        """
        if job_id in self._jobs:
            del self._jobs[job_id]
            logger.debug("Job deleted: %s", job_id)
            return True
        return False


# ── SINGLETON ─────────────────────────────────────────────────────
# One instance shared across the entire app.
# Imported by services — never instantiated elsewhere.
job_dao = JobDAO()