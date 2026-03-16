# agents/config/agent_types.py

from __future__ import annotations
from typing     import TypedDict, Optional, Literal
from dataclasses import dataclass
from enum       import Enum
from shared.types import RawOutput


# ── LITERALS ──────────────────────────────────────────

CrewAgentName = Literal[
    "web_agent",
    "review_agent",
    "news_agent",
    "seo_agent",
]


# ── ENUMS ─────────────────────────────────────────────

class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED  = "failed"


# ── TYPEDICTS ─────────────────────────────────────────
# AgentResult stays TypedDict — it's never iterated over,
# only accessed by key. TypedDict is fine for that.

class AgentResult(TypedDict):
    """
    Result from one CrewAI agent after finishing its task.
    """
    agent:   CrewAgentName
    output:  RawOutput
    success: bool
    error:   Optional[str]


# ── DATACLASS ─────────────────────────────────────────
# CrewResults becomes a dataclass — NOT a TypedDict.
#
# Why switch from TypedDict to dataclass here?
# TypedDict is a dict internally — when you call .items()
# Pylance widens the value type to `object` and loses
# all type information. You can't iterate it cleanly.
#
# dataclass is a real class — Pylance knows the exact
# type of every field always. You can iterate with
# dataclasses.fields() and get full type safety.
# You can also add methods like .all_results() cleanly.
#
# Rule of thumb:
# TypedDict  → when you need a typed dict (JSON, LangGraph state)
# dataclass  → when you need a typed object with methods

@dataclass
class CrewResults:
    """
    Combined results from all 4 CrewAI research agents.
    Returned by crew_runner.py after all agents finish.
    Orchestrator reads this and writes into PipelineState.
    """
    web_agent:    AgentResult
    review_agent: AgentResult
    news_agent:   AgentResult
    seo_agent:    AgentResult

    def all_results(self) -> list[tuple[str, AgentResult]]:
        """
        Returns all agent results as a list of (name, result) tuples.
        Used for logging and iteration — clean, typed, no widening.

        Returns:
            List of tuples — each is (agent_name, AgentResult)
        """
        return [
            ("web_agent",    self.web_agent),
            ("review_agent", self.review_agent),
            ("news_agent",   self.news_agent),
            ("seo_agent",    self.seo_agent),
        ]

    def any_succeeded(self) -> bool:
        """Returns True if at least one agent produced output."""
        return any(
            r["success"]
            for _, r in self.all_results()
        )

    def success_count(self) -> int:
        """Returns how many agents succeeded."""
        return sum(
            1 for _, r in self.all_results()
            if r["success"]
        )