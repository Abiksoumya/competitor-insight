# The pipeline flow definition# pipeline/graph.py
# ─────────────────────────────────────────────────────
# LangGraph pipeline definition.
# Wires research_node → analyst_node into a graph.
#
# What is LangGraph?
# A framework for building stateful multi-step AI pipelines.
# You define NODES (steps) and EDGES (connections between steps).
# State flows through the graph — each node reads and updates it.
#
# Our graph is simple — two nodes, one edge:
#
#   START → research_node → analyst_node → END
#
# Why use LangGraph at all if it's this simple?
# 1. Makes it easy to add conditional logic later
#    (e.g. skip analyst if research failed)
# 2. Built-in state management — no manual passing of data
# 3. Easy to add more nodes (e.g. fact-check node, export node)
# 4. Industry standard for production agentic pipelines
# ─────────────────────────────────────────────────────

from __future__ import annotations
from langgraph.graph import StateGraph, START, END
from config.logging_config          import get_logger
from pipeline.config.pipeline_types import PipelineState
from pipeline.state                 import create_initial_state
from agents.orchestrator_agent      import research_node, analyst_node
from shared.types                   import Url, Markdown
from langgraph.graph.state import CompiledStateGraph  # ← add this import
from typing import cast  # ← add to imports


logger = get_logger(__name__)


def build_pipeline() -> CompiledStateGraph:
    """
    Builds and compiles the LangGraph pipeline.

    A StateGraph takes a TypedDict as its state schema.
    Every node in the graph receives the full state and
    returns an updated version of it.

    Graph structure:
        START → research_node → analyst_node → END

    Returns:
        Compiled LangGraph pipeline ready to run
    """
    logger.debug("Building LangGraph pipeline")

    # Create graph with PipelineState as the shared state schema
    # Every node receives PipelineState and returns PipelineState
    graph = StateGraph(PipelineState)

    # ── ADD NODES ─────────────────────────────────────
    # Nodes are just Python functions that take and return state
    graph.add_node("research", research_node)
    graph.add_node("analyst",  analyst_node)
    # "research" and "analyst" are node names —
    # used when defining edges below

    # ── ADD EDGES ─────────────────────────────────────
    # Edges define the flow: what runs after what

    # START → research_node
    # START is a special LangGraph constant — the entry point
    graph.add_edge(START, "research")

    # research_node → analyst_node
    graph.add_edge("research", "analyst")

    # analyst_node → END
    # END is a special LangGraph constant — the exit point
    graph.add_edge("analyst", END)

    # ── COMPILE ───────────────────────────────────────
    # compile() validates the graph and prepares it for execution
    # Raises an error if any node or edge is misconfigured
    compiled = graph.compile()

    logger.debug("Pipeline compiled successfully")

    return compiled


def run_pipeline(url: Url) -> Markdown:
    """
    Runs the full competitor intelligence pipeline for a URL.

    This is the single public entry point for the entire system.
    Called by pipeline_service.py when a job starts.

    Flow:
        1. Create initial state with the URL
        2. Build and compile the LangGraph pipeline
        3. Run the pipeline — research then analyst
        4. Extract and return the final report

    Args:
        url: Competitor URL submitted by the user

    Returns:
        Final markdown intelligence report
    """
    logger.info("Pipeline starting — url: %s", url)

    # Create fresh state for this job
    initial_state = create_initial_state(url)

    # Build the pipeline
    pipeline = build_pipeline()

    # Run the pipeline — blocks until complete
    # invoke() runs the graph synchronously from START to END
    # and returns the final state after all nodes have run
    final_state = cast(PipelineState, pipeline.invoke(initial_state))

    # Extract the report from final state
    report: Markdown = final_state.get("final_report", "")

    if not report:
        error = final_state.get("error", "Unknown error")
        logger.error("Pipeline completed but no report generated: %s", error)
        raise ValueError(f"Pipeline failed: {error}")

    logger.info(
        "Pipeline complete — report length: %d chars",
        len(report)
    )

    return report