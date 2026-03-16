# pipeline/crew_runner.py
# ─────────────────────────────────────────────────────
# Builds and runs the CrewAI research crew.
# Called by orchestrator_agent.py → research_node()
#
# CrewAI 1.10.1 removed Process.parallel.
# We achieve parallelism by running 4 SEPARATE single-agent
# crews simultaneously using asyncio.gather().
#
# Why asyncio.gather()?
# It runs all 4 coroutines concurrently in the same event loop.
# All 4 agents start at the same time and we wait for all to finish.
# Total time = slowest agent, not sum of all agents.
#
# Sequential: web(30s) + review(30s) + news(20s) + seo(20s) = 100s
# Parallel:   max(30s, 30s, 20s, 20s)                       =  30s
# ─────────────────────────────────────────────────────

from __future__ import annotations
import asyncio
import re

from crewai import Crew, Task, Process
from config.logging_config          import get_logger
from shared.types                   import Url, CompanyName
from agents.config.agent_types      import AgentResult, CrewResults
from agents.web_agent               import web_agent
from agents.review_agent            import review_agent
from agents.news_agent              import news_agent
from agents.seo_agent               import seo_agent

logger = get_logger(__name__)


# ── COMPANY NAME EXTRACTOR ────────────────────────────────────────

def _extract_company_name(url: Url) -> CompanyName:
    """
    Extracts a human-readable company name from a URL.

    Examples:
        "https://www.notion.so"   → "Notion"
        "https://speel.ai"        → "Speel"
        "https://www.hubspot.com" → "Hubspot"

    Args:
        url: Competitor URL

    Returns:
        Capitalized domain name as company name
    """
    domain = re.sub(r"https?://(www\.)?", "", url)
    name   = domain.split(".")[0].split("/")[0]
    return name.capitalize()


# ── TASK BUILDERS ─────────────────────────────────────────────────
# Built fresh per job — contains the specific URL and company
# name for THIS run, not a previous one.

def _build_web_task(url: Url) -> Task:
    return Task(
        description=(
            f"Scrape the competitor website at {url}. "
            f"Visit the homepage, pricing page, and features page. "
            f"Extract: product name, tagline, key features, "
            f"all pricing tiers with prices, integrations, "
            f"target audience, and tech stack signals. "
            f"If a page fails to load, continue with other pages."
        ),
        expected_output=(
            "Structured summary with: "
            "1) Product name and tagline "
            "2) Key features list "
            "3) Pricing tiers with prices "
            "4) Integrations list "
            "5) Target audience "
            "6) Tech stack clues"
        ),
        agent=web_agent,
    )


def _build_review_task(company_name: CompanyName) -> Task:
    return Task(
        description=(
            f"Mine customer reviews for {company_name} from G2 "
            f"and Trustpilot. Collect reviews and identify the "
            f"top recurring themes in positive reviews AND the "
            f"top recurring complaints. "
            f"Complaints are more valuable — dig deep into them. "
            f"Look for patterns, not one-off opinions."
        ),
        expected_output=(
            "Structured sentiment report with: "
            "1) Top 5 things customers love (with evidence) "
            "2) Top 5 complaints and pain points (with evidence) "
            "3) Most common use case mentioned "
            "4) Overall sentiment summary in 2 sentences"
        ),
        agent=review_agent,
    )


def _build_news_task(company_name: CompanyName) -> Task:
    return Task(
        description=(
            f"Research recent news for {company_name}. "
            f"Focus on the last 6 months only. "
            f"Find: funding rounds, product launches, "
            f"new features, key hires, partnerships, press coverage. "
            f"Identify signals that reveal what they are building next."
        ),
        expected_output=(
            "Business intelligence report with: "
            "1) Recent funding rounds "
            "2) Product launches and new features "
            "3) Key hires or leadership changes "
            "4) Notable partnerships announced "
            "5) Growth signals and strategic direction"
        ),
        agent=news_agent,
    )


def _build_seo_task(url: Url, company_name: CompanyName) -> Task:
    domain = re.sub(r"https?://", "", url).split("/")[0]
    return Task(
        description=(
            f"Analyze SEO and content strategy for {company_name} "
            f"at domain {domain}. "
            f"Find: primary keywords they target, content topics "
            f"they publish, posting frequency, and content gaps — "
            f"topics their audience wants but they don't cover."
        ),
        expected_output=(
            "SEO and content report with: "
            "1) Primary keywords they target "
            "2) Content topics and themes "
            "3) Publishing frequency estimate "
            "4) Target audience signals "
            "5) Content gaps and missed opportunities"
        ),
        agent=seo_agent,
    )


# ── SINGLE CREW RUNNER ────────────────────────────────────────────

async def _run_single_agent_crew(
    task:       Task,
    agent_name: str,
) -> AgentResult:

    logger.info("Starting agent: %s", agent_name)

    try:
        assert task.agent is not None, (
            f"Agent for task '{agent_name}' is None"
        )

        crew = Crew(
            agents=[task.agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        )

        # ── FIX: cast to CrewOutput ────────────────────
        # kickoff_async() is annotated as returning CrewStreamingOutput
        # in CrewAI 1.10.1 — but actually returns CrewOutput at runtime.
        # cast() tells Pylance: "treat this as CrewOutput"
        # cast() does NOTHING at runtime — zero performance cost.
        # It is purely a type hint instruction for the type checker.
        from typing import cast
        from crewai import CrewOutput

        raw_crew_output = await crew.kickoff_async()
        crew_output = cast(CrewOutput, raw_crew_output)
        # Now Pylance knows crew_output has .tasks_output ✅

        raw_output: str = ""
        if crew_output.tasks_output:
            raw = crew_output.tasks_output[0].raw
            raw_output = str(raw) if raw else ""

        success = bool(raw_output)

        logger.info(
            "Agent %s finished — %d chars — success: %s",
            agent_name, len(raw_output), success
        )

        return AgentResult(
            agent=agent_name,       # type: ignore[arg-type]
            output=raw_output,
            success=success,
            error=None,
        )

    except AssertionError as e:
        logger.error("Agent configuration error: %s", str(e))
        return AgentResult(
            agent=agent_name,       # type: ignore[arg-type]
            output="",
            success=False,
            error=str(e),
        )

    except Exception as e:
        logger.error("Agent %s failed: %s", agent_name, str(e))
        return AgentResult(
            agent=agent_name,       # type: ignore[arg-type]
            output="",
            success=False,
            error=str(e),
        )


# ── MAIN FUNCTION ─────────────────────────────────────────────────

async def _run_all_agents_async(
    url:          Url,
    company_name: CompanyName,
) -> CrewResults:
    """
    Runs all 4 research agents concurrently using asyncio.gather().

    asyncio.gather() takes multiple coroutines and runs them
    all at the same time in the same event loop.
    It waits until ALL of them finish before returning.

    return_exceptions=True means:
        If one agent crashes → returns the Exception as its result
        Other agents keep running — no cascade failure
        We handle the exception in _run_single_agent_crew above
        so results always come back as AgentResult, not Exception

    Args:
        url:          Competitor URL
        company_name: Extracted company name

    Returns:
        CrewResults with one AgentResult per agent
    """
    # Build tasks fresh for this specific job
    web_task    = _build_web_task(url)
    review_task = _build_review_task(company_name)
    news_task   = _build_news_task(company_name)
    seo_task    = _build_seo_task(url, company_name)

    logger.info(
        "Launching 4 agents in parallel — company: %s",
        company_name
    )

    # Run all 4 concurrently — this is the parallel magic
    results = await asyncio.gather(
        _run_single_agent_crew(web_task,    "web_agent"),
        _run_single_agent_crew(review_task, "review_agent"),
        _run_single_agent_crew(news_task,   "news_agent"),
        _run_single_agent_crew(seo_task,    "seo_agent"),
        return_exceptions=True,
    )

    # results is a tuple of 4 items in the same order as gather()
    # Unpack by position — order is guaranteed by asyncio.gather
    web_result, review_result, news_result, seo_result = results

    # Handle case where return_exceptions=True returned an Exception
    # instead of AgentResult (shouldn't happen since we catch inside
    # _run_single_agent_crew, but defensive check is good practice)
    def _safe_result(
        result: AgentResult | BaseException,
        agent_name: str,
    ) -> AgentResult:
        if isinstance(result, BaseException):
            logger.error(
                "Unhandled exception from %s: %s",
                agent_name, str(result)
            )
            return AgentResult(
                agent=agent_name,   # type: ignore[arg-type]
                output="",
                success=False,
                error=str(result),
            )
        return result

    crew_results = CrewResults(
        web_agent=_safe_result(web_result,    "web_agent"),
        review_agent=_safe_result(review_result, "review_agent"),
        news_agent=_safe_result(news_result,  "news_agent"),
        seo_agent=_safe_result(seo_result,    "seo_agent"),
    )

    # Log summary
    crew_results = CrewResults(
    web_agent=_safe_result(web_result,    "web_agent"),
    review_agent=_safe_result(review_result, "review_agent"),
    news_agent=_safe_result(news_result,  "news_agent"),
    seo_agent=_safe_result(seo_result,    "seo_agent"),
)

# ── LOG SUMMARY ───────────────────────────────────────
# .all_results() returns list[tuple[str, AgentResult]]
# Pylance knows exact type of `result` — no widening
    for name, result in crew_results.all_results():
        icon = "✓" if result["success"] else "✗"
        logger.info(
            "  %s %s — %d chars",
            icon, name, len(result["output"])
        )

    return crew_results


def run_research_crew(
    url:          Url,
    company_name: CompanyName = "",
) -> CrewResults:
    """
    Public entry point — called by orchestrator_agent.py.
    Synchronous wrapper around the async implementation.

    Why a sync wrapper?
    LangGraph nodes are synchronous functions.
    asyncio.run() creates a fresh event loop, runs the async
    function to completion, and returns the result.
    This bridges the sync LangGraph world with async CrewAI.

    Args:
        url:          Competitor URL to research
        company_name: Company name — extracted from URL if empty

    Returns:
        CrewResults with one AgentResult per research agent
    """
    if not company_name:
        company_name = _extract_company_name(url)
        logger.info("Extracted company name: %s", company_name)

    return asyncio.run(
        _run_all_agents_async(url, company_name)
    )