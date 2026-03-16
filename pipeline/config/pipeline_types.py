# pipeline/config/pipeline_types.py
# ─────────────────────────────────────────────────────
# Types used only inside the pipeline/ folder.
# PipelineState is the shared memory of the entire system.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from typing   import TypedDict, Optional
from shared.types import Url, RawOutput, Markdown, CompanyName


class PipelineState(TypedDict):
    """
    Shared state passed between every LangGraph node.

    Think of this as the whiteboard in a meeting room.
    Every node reads what it needs and writes its result.
    Nobody passes data directly to another node —
    they all communicate through this shared object.

    Lifecycle:
        create_initial_state(url)
            ↓
        research_node  → fills raw_website, raw_reviews,
                          raw_news, raw_seo
            ↓
        analyst_node   → fills final_report
            ↓
        status = DONE
    """

    # ── INPUT ──────────────────────────────────────
    url:          Url           # Competitor URL from user

    # ── EXTRACTED ──────────────────────────────────
    company_name: CompanyName   # Parsed from URL or website

    # ── RAW AGENT OUTPUTS ──────────────────────────
    # Empty string = agent has not run yet
    raw_website:  RawOutput     # From web_agent
    raw_reviews:  RawOutput     # From review_agent
    raw_news:     RawOutput     # From news_agent
    raw_seo:      RawOutput     # From seo_agent

    # ── FINAL OUTPUT ───────────────────────────────
    final_report: Markdown      # From analyst_agent

    # ── TRACKING ───────────────────────────────────
    status:       str           # JobStatus enum value
    error:        Optional[str] # None unless pipeline failed