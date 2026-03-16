# agents/analyst_agent.py
# ─────────────────────────────────────────────────────
# Synthesizes all research into the final report.
# Supports multiple LLM providers — switch via .env
#
# ANALYST_PROVIDER=anthropic  → production (best quality)
# ANALYST_PROVIDER=gemini     → testing (free tier)
# ANALYST_PROVIDER=groq       → testing (fast + free)
#
# Zero code changes needed to switch — just update .env
# ─────────────────────────────────────────────────────

from __future__ import annotations
from config.settings       import settings
from config.logging_config import get_logger
from shared.types          import Markdown
from pipeline.config.pipeline_types import PipelineState

logger = get_logger(__name__)


# ── SYNTHESIS PROMPT ──────────────────────────────────────────────
# Same prompt regardless of provider — consistent output format

SYNTHESIS_PROMPT = """
You are a senior competitive intelligence analyst.
You have been given raw research data about a competitor company
collected by 4 specialized research agents.

Your job is to synthesize ALL of this raw data into a structured,
actionable 5-section intelligence report.

RAW RESEARCH DATA:
==================
WEBSITE ANALYSIS:
{raw_website}

CUSTOMER REVIEWS:
{raw_reviews}

RECENT NEWS & FUNDING:
{raw_news}

SEO & CONTENT STRATEGY:
{raw_seo}
==================

Write a report with EXACTLY these 5 sections in this order.
Use markdown formatting. Be specific — no vague statements.
Every insight must be backed by the research data above.

## 1. Company Overview
- Founded, funding status, team size estimate
- Core product in one sentence
- Target customer and primary use case
- Key differentiator vs the market

## 2. Product Analysis
- Top 5 features (with brief description of each)
- Pricing tiers (names, prices, what's included)
- Notable integrations
- Apparent tech stack signals
- Product limitations or gaps

## 3. Customer Sentiment
- Top 3 things customers LOVE (with evidence from reviews)
- Top 3 things customers COMPLAIN about (these are opportunities)
- Overall sentiment summary
- Most common use case mentioned by users

## 4. Marketing & SEO Strategy
- Primary keywords they target
- Content topics they publish
- Posting frequency estimate
- Target audience signals from their content
- Content gaps — topics their audience wants but they miss

## 5. Strategic Recommendations
- 3 specific ways to beat or differentiate from this competitor
- Their biggest weakness your product can exploit
- The customer segment they underserve
- One immediate action to take based on this research

Keep each section focused and actionable.
Write for a founder or product manager making strategic decisions.
"""


# ── PROVIDER FUNCTIONS ────────────────────────────────────────────

def _run_anthropic(prompt: str) -> Markdown:
    """
    Calls Claude API for synthesis.
    Used in production — best report quality.
    """
    import anthropic
    from anthropic.types import TextBlock

    logger.info("Using Anthropic Claude for synthesis")

    client = anthropic.Anthropic(
        api_key=settings.ANTHROPIC_API_KEY
    )

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=settings.CLAUDE_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    text_blocks = [
        block for block in response.content
        if isinstance(block, TextBlock)
    ]

    if not text_blocks:
        raise ValueError("Claude returned no text content")

    return text_blocks[0].text


def _run_gemini(prompt: str) -> Markdown:
    # Switch to new SDK
    from google import genai  # type: ignore[import]

    logger.info("Using Gemini for synthesis")

    if not settings.GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not set in .env"
        )

    client = genai.Client(api_key=settings.GEMINI_API_KEY)  # type: ignore[attr-defined]

    response = client.models.generate_content(  # type: ignore[attr-defined]
        model="gemini-2.0-flash",
        contents=prompt,
    )

    return str(response.text)


def _run_groq(prompt: str) -> Markdown:
    from groq import Groq

    logger.info("Using Groq for synthesis")

    if not settings.GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set in .env — "
            "get a free key at console.groq.com"
        )

    client = Groq(api_key=settings.GROQ_API_KEY)

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,  # ← reads from settings, not hardcoded
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
    )

    content = response.choices[0].message.content
    return str(content) if content else ""


# ── ROUTER ────────────────────────────────────────────────────────

def _route_to_provider(prompt: str) -> Markdown:
    """
    Routes to the correct LLM provider based on ANALYST_PROVIDER.

    This is the Strategy Pattern:
    - One interface: _route_to_provider(prompt) → Markdown
    - Multiple implementations: anthropic, gemini, groq
    - Selection controlled by config — not by code changes

    Adding a new provider = add one function + one elif.
    Zero changes needed anywhere else in the codebase.
    """
    provider = settings.ANALYST_PROVIDER.lower().strip()

    logger.info("Analyst provider: %s", provider)

    if provider == "anthropic":
        return _run_anthropic(prompt)
    elif provider == "gemini":
        return _run_gemini(prompt)
    elif provider == "groq":
        return _run_groq(prompt)
    else:
        raise ValueError(
            f"Unknown ANALYST_PROVIDER '{provider}' in .env — "
            f"valid options: anthropic, gemini, groq"
        )


# ── PUBLIC FUNCTION ───────────────────────────────────────────────

def run_analyst(state: PipelineState) -> Markdown:
    """
    Synthesizes all research into the final 5-section report.
    Called by analyst_node() in orchestrator_agent.py.

    Args:
        state: PipelineState with all raw_* fields filled

    Returns:
        Final markdown intelligence report
    """
    logger.info(
        "Analyst starting synthesis — provider: %s",
        settings.ANALYST_PROVIDER
    )

    # Log warnings for empty research fields
    for field in ["raw_website", "raw_reviews", "raw_news", "raw_seo"]:
        if not state[field]:
            logger.warning(
                "Field '%s' is empty — partial report will be generated",
                field
            )

    # Build prompt with research data
    prompt: str = SYNTHESIS_PROMPT.format(
        raw_website=state["raw_website"] or "No website data collected.",
        raw_reviews=state["raw_reviews"] or "No review data collected.",
        raw_news=state["raw_news"]        or "No news data collected.",
        raw_seo=state["raw_seo"]          or "No SEO data collected.",
    )

    try:
        report = _route_to_provider(prompt)
        logger.info(
            "Synthesis complete — %d chars",
            len(report)
        )
        return report

    except Exception as e:
        error_msg = f"Analyst agent failed: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)