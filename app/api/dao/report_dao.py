# app/dao/report_dao.py
# ─────────────────────────────────────────────────────
# Data Access Object for reports.
# Stores completed reports in memory.
#
# One report per job — keyed by job_id.
# Reports are immutable once created.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from typing import Optional
from app.api.models.domain_models import ReportRecord
from config.logging_config import get_logger

logger = get_logger(__name__)


class ReportDAO:
    """
    In-memory storage for completed intelligence reports.

    Storage:
        _reports: dict[job_id, ReportRecord]
        key   = job_id string
        value = ReportRecord dataclass
    """

    def __init__(self) -> None:
        self._reports: dict[str, ReportRecord] = {}
        logger.debug("ReportDAO initialized")

    def save(self, report: ReportRecord) -> None:
        """
        Saves a completed report.
        Reports are write-once — saving twice overwrites.

        Args:
            report: ReportRecord to save
        """
        self._reports[report.job_id] = report
        logger.debug(
            "Report saved: job_id=%s url=%s",
            report.job_id, report.url
        )

    def get(self, job_id: str) -> Optional[ReportRecord]:
        """
        Retrieves a report by job ID.
        Returns None if report does not exist yet.

        Args:
            job_id: UUID string identifying the job

        Returns:
            ReportRecord if found, None if not ready yet
        """
        return self._reports.get(job_id)

    def exists(self, job_id: str) -> bool:
        """
        Checks if a report exists for a given job.

        Args:
            job_id: UUID string to check

        Returns:
            True if report is ready, False otherwise
        """
        return job_id in self._reports

    def count(self) -> int:
        """Returns total number of reports stored."""
        return len(self._reports)


# ── SINGLETON ─────────────────────────────────────────────────────
report_dao = ReportDAO()