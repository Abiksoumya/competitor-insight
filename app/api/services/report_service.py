# app/services/report_service.py
# ─────────────────────────────────────────────────────
# Handles report storage and retrieval.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from typing   import Optional
from datetime import datetime

from config.logging_config    import get_logger
from shared.types             import JobId, Url, Markdown
from app.api.dao.report_dao       import report_dao
from app.api.models.domain_models import ReportRecord

logger = get_logger(__name__)


class ReportService:
    """
    Handles saving and retrieving completed reports.
    Called by pipeline_service after pipeline finishes.
    Called by report_controller when user polls for results.
    """

    def save_report(
        self,
        job_id: JobId,
        url:    Url,
        content: Markdown,
    ) -> ReportRecord:
        """
        Saves a completed intelligence report.
        Called by pipeline_service after successful run.

        Args:
            job_id:  UUID of the completed job
            url:     Competitor URL that was analyzed
            content: Final markdown report from analyst

        Returns:
            Saved ReportRecord
        """
        report = ReportRecord(
            job_id=job_id,
            url=url,
            content=content,
            created_at=datetime.now(),
        )

        report_dao.save(report)

        logger.info(
            "Report saved: job_id=%s length=%d chars",
            job_id, len(content)
        )

        return report

    def get_report(self, job_id: JobId) -> Optional[ReportRecord]:
        """
        Retrieves a report by job ID.
        Returns None if report is not ready yet.

        Args:
            job_id: UUID string

        Returns:
            ReportRecord if ready, None if not yet complete
        """
        return report_dao.get(job_id)

    def report_exists(self, job_id: JobId) -> bool:
        """
        Checks if a report exists for a job.

        Args:
            job_id: UUID string

        Returns:
            True if report is ready
        """
        return report_dao.exists(job_id)


# Singleton
report_service = ReportService()