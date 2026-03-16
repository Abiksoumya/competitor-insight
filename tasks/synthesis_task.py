# tasks/synthesis_task.py
# ─────────────────────────────────────────────────────
# Synthesis task is different from the 4 research tasks.
# It does NOT use CrewAI — it calls Claude API directly
# via analyst_agent.py → run_analyst().
#
# This file exists for consistency — one task file per agent.
# It provides the build function pattern other tasks use,
# but returns a description dict instead of a CrewAI Task.
#
# Why not a CrewAI Task here?
# The analyst needs all 4 research outputs passed in together.
# CrewAI Tasks don't support passing structured data this way.
# Direct Claude API call gives us full control over the prompt.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from shared.types                   import Markdown
from pipeline.config.pipeline_types import PipelineState
from agents.analyst_agent           import run_analyst


def build_synthesis_task(state: PipelineState) -> Markdown:
    """
    Runs the synthesis task — calls analyst_agent directly.

    This is the final step in the pipeline.
    Takes all 4 raw research outputs from PipelineState
    and synthesizes them into the final 5-section report.

    Why not return a CrewAI Task like other task files?
    The analyst uses Claude API directly — not CrewAI.
    This function IS the task execution, not just a template.

    Args:
        state: PipelineState with all raw_* fields filled
               by the 4 research agents

    Returns:
        Final markdown intelligence report
    """
    return run_analyst(state)