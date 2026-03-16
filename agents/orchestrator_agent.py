# ← LangGraph — controls the whole pipeline
# agents/orchestrator_agent.py
# ─────────────────────────────────────────────────────
# Controls the entire pipeline flow.
# This is NOT a CrewAI agent — it is a LangGraph node.
#
# What is the difference?
# CrewAI agent → does research work (scrape, search, analyze)
# LangGraph node → controls FLOW (what runs next, what state is)
#
# The orchestrator:
# 1. Receives the initial URL from FastAPI
# 2. Triggers the CrewAI research crew
# 3. Takes crew results and writes them into PipelineState
# 4. Triggers the analyst agent
# 5. Takes the final report and marks the job done
#
# It lives in agents/ because it IS an agent conceptually —
# it just uses LangGraph instead of CrewAI.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from config.logging_config          import get_logger
from shared.types                   import JobStatus
from pipeline.config.pipeline_types import PipelineState
from pipeline.crew_runner import run_research_crew
from agents.analyst_agent           import run_analyst

logger = get_logger(__name__)


def research_node(state: PipelineState) -> PipelineState:
    """
    LangGraph node — runs the CrewAI research crew.

    This is the first node in the pipeline graph.
    It takes the URL from state, runs all 4 research agents
    in parallel via CrewAI, and writes their outputs back
    into the shared PipelineState.

    Why write results back into state?
    LangGraph nodes communicate through state — not return values.
    Each node receives the full state, modifies its fields,
    and returns the updated state for the next node to read.

    Args:
        state: Current PipelineState — only url is filled at this point

    Returns:
        Updated PipelineState with all raw_* fields filled
    """
    logger.info(
        "Research node starting — url: %s",
        state["url"]
    )

    try:
        # Run all 4 CrewAI agents in parallel
        # crew_runner handles the CrewAI setup and execution
        crew_results = run_research_crew(
            url=state["url"],
            company_name=state["company_name"],
        )

        # Write each agent's output into state
        # These fields are read by the analyst node next
        updated_state: PipelineState = {
            **state,

            "raw_website": (
                crew_results.web_agent["output"]
                if crew_results.web_agent["success"]
                else ""
            ),
            "raw_reviews": (
                crew_results.review_agent["output"]
                if crew_results.review_agent["success"]
                else ""
            ),
            "raw_news": (
                crew_results.news_agent["output"]
                if crew_results.news_agent["success"]
                else ""
            ),
            "raw_seo": (
                crew_results.seo_agent["output"]
                if crew_results.seo_agent["success"]
                else ""
            ),
            "status": JobStatus.RUNNING,
        }

        logger.info("Research node complete — all agents finished")
        return updated_state

    except Exception as e:
        logger.error("Research node failed: %s", str(e))
        return {
            **state,
            "status": JobStatus.FAILED,
            "error": str(e),
        }


def analyst_node(state: PipelineState) -> PipelineState:
    """
    LangGraph node — runs the Claude analyst agent.

    This is the second and final node in the pipeline.
    It receives the state with all raw research data filled,
    calls the analyst agent to synthesize the final report,
    and writes it back into state.

    Args:
        state: PipelineState with all raw_* fields filled

    Returns:
        Updated PipelineState with final_report filled
        and status set to DONE or FAILED
    """
    logger.info("Analyst node starting synthesis")

    try:
        # Run Claude synthesis
        final_report = run_analyst(state)

        logger.info("Analyst node complete")

        return {
            **state,
            "final_report": final_report,
            "status": JobStatus.DONE,
            "error": None,
        }

    except Exception as e:
        logger.error("Analyst node failed: %s", str(e))
        return {
            **state,
            "status": JobStatus.FAILED,
            "error": str(e),
        }