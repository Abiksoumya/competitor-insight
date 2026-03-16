# app/models/domain_models.py

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from app.api.models.response_models import JobStatus


@dataclass
class JobRecord:
    """
    Internal representation of a job.
    Used by JobDAO to store and retrieve job state.
    NOT exposed to the user directly.

    Why dataclass instead of Pydantic here?
    This is internal data — no HTTP validation needed.
    dataclass is lighter and faster for internal use.
    """
    job_id:       str
    url:          str
    status:       JobStatus        = JobStatus.QUEUED
    created_at:   datetime         = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error:        Optional[str]    = None

    def mark_running(self) -> None:
        """Transition job to running state"""
        self.status = JobStatus.RUNNING

    def mark_done(self) -> None:
        """Transition job to done state"""
        self.status     = JobStatus.DONE
        self.completed_at = datetime.now()

    def mark_failed(self, error: str) -> None:
        """Transition job to failed state with error message"""
        self.status       = JobStatus.FAILED
        self.error        = error
        self.completed_at = datetime.now()


@dataclass
class ReportRecord:
    """
    Internal representation of a completed report.
    Used by ReportDAO to store and retrieve reports.
    """
    job_id:     str
    url:        str
    content:    str               # Full markdown report from Claude
    created_at: datetime = field(default_factory=datetime.now)