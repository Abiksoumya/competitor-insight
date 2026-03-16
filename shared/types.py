# shared/types.py
# ─────────────────────────────────────────────────────
# ONLY types that are used by MORE than one folder.
# If a type is only used in agents/ → it does NOT belong here.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from enum import Enum


# ── PRIMITIVE ALIASES ─────────────────────────────────
# Used across agents, pipeline, models, services — truly shared

Url         = str   # "https://competitor.com"
JobId       = str   # "3f2a-bc91-..."
Markdown    = str   # "## Report\n..."
RawOutput   = str   # raw unprocessed agent output
CompanyName = str   # "Speel"


# ── SHARED ENUMS ──────────────────────────────────────
# JobStatus is used by pipeline, services, dao, models — shared

class JobStatus(str, Enum):
    """
    Lifecycle of a background pipeline job.
    Used by: pipeline, services, dao, models — so lives in shared/
    """
    QUEUED  = "queued"
    RUNNING = "running"
    DONE    = "done"
    FAILED  = "failed"