# tasks/config/task_types.py
# ─────────────────────────────────────────────────────
# Types used only inside the tasks/ folder.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from typing     import TypedDict, Optional
from enum       import Enum
from shared.types import RawOutput


class TaskStatus(str, Enum):
    """
    Completion status of a CrewAI task.
    Separate from AgentStatus — a task can be retried
    multiple times across agent attempts.
    """
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"


class TaskResult(TypedDict):
    """
    Structured result from a single CrewAI task.
    Each task file's build function returns one of these
    after the task completes.
    """
    task_name: str
    output:    RawOutput
    status:    str          # TaskStatus value
    error:     Optional[str]