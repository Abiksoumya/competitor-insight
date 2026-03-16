# app/models/response_models.py

from pydantic import BaseModel
from typing import Optional
from enum import Enum


from shared.types import JobStatus  # ← import from single source of truth



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