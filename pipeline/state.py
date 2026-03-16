# pipeline/state.py
# ─────────────────────────────────────────────────────
# Factory function that creates a fresh PipelineState.
# Called by pipeline_service.py when a new job starts.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from shared.types                   import Url
from shared.types                   import JobStatus
from pipeline.config.pipeline_types import PipelineState


def create_initial_state(url: Url) -> PipelineState:
    """
    Creates a fresh PipelineState with all fields at defaults.

    Why a factory function?
    Single place to update if PipelineState gains a new field.
    Every caller gets the same guaranteed-complete starting state.
    No risk of forgetting to initialize a field somewhere.

    Args:
        url: Competitor URL submitted by user

    Returns:
        PipelineState ready to be passed into the LangGraph pipeline
    """
    return PipelineState(
        url=url,
        company_name="",
        raw_website="",
        raw_reviews="",
        raw_news="",
        raw_seo="",
        final_report="",
        status=JobStatus.RUNNING,
        error=None,
    )