# app/models/response_models.py

from pydantic import BaseModel
from typing import Optional
from enum import Enum


class JobStatus(str, Enum):
    """
    Why inherit from both str AND Enum?
    - Enum: gives you the fixed set of values
    - str:  makes it JSON serializable automatically
    Without str, FastAPI would fail to serialize JobStatus.DONE to JSON.
    """
    QUEUED  = "queued"
    RUNNING = "running"
    DONE    = "done"
    FAILED  = "failed"


class AnalyzeResponse(BaseModel):
    job_id:  str
    status:  JobStatus
    message: str = "Analysis started. Poll /report/{job_id} for results."


class ReportResponse(BaseModel):
    job_id:  str
    status:  JobStatus
    report:  Optional[str] = None
    error:   Optional[str] = None

    def is_ready(self) -> bool:
        """Convenience method — check if report is ready to read"""
        return self.status == JobStatus.DONE and self.report is not None


class HealthResponse(BaseModel):
    status:  str = "ok"
    version: str