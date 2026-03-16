# Task for news_agent# tasks/news_research_task.py
# ─────────────────────────────────────────────────────
# Task template for news_agent.
# Finds recent funding, launches, and strategic signals.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from crewai  import Task
from agents.news_agent import news_agent
from shared.types      import CompanyName


def build_news_research_task(company_name: CompanyName) -> Task:
    """
    Builds a configured news research task for a specific company.

    Args:
        company_name: Company name to research

    Returns:
        Configured CrewAI Task assigned to news_agent
    """
    return Task(
        description=(
            f"Research recent news and business intelligence "
            f"for {company_name}. Focus on the last 6 months.\n\n"

            f"INSTRUCTIONS:\n"
            f"1. Search for funding and financial news:\n"
            f"   '{company_name} funding round 2025'\n"
            f"   '{company_name} investment series'\n\n"

            f"2. Search for product news:\n"
            f"   '{company_name} product launch 2025'\n"
            f"   '{company_name} new feature announcement'\n\n"

            f"3. Search for strategic signals:\n"
            f"   '{company_name} partnership announcement'\n"
            f"   '{company_name} acquisition'\n"
            f"   '{company_name} hiring engineers'\n\n"

            f"4. Use Recent News Search for time-sensitive queries.\n"
            f"   Use Web Search for broader context queries.\n\n"

            f"5. Read between the lines — a job posting for\n"
            f"   ML engineers signals an AI product coming.\n"
            f"   A Series B signals aggressive expansion plans."
        ),

        expected_output=(
            "A business intelligence report containing:\n\n"
            "1. FUNDING & FINANCIALS\n"
            "   - Most recent funding round (amount, date, investors)\n"
            "   - Total funding raised if known\n"
            "   - What the funding signals about their plans\n\n"
            "2. RECENT PRODUCT LAUNCHES\n"
            "   - New features or products launched in last 6 months\n"
            "   - What problem each launch addresses\n\n"
            "3. STRATEGIC MOVES\n"
            "   - Partnerships or integrations announced\n"
            "   - Acquisitions if any\n"
            "   - Market expansion signals\n\n"
            "4. HIRING SIGNALS\n"
            "   - Key roles they are hiring for\n"
            "   - What these hires signal about product direction\n\n"
            "5. STRATEGIC DIRECTION\n"
            "   - Overall assessment of where they are heading\n"
            "   - Timeline estimate for their next major move"
        ),

        agent=news_agent,
    )