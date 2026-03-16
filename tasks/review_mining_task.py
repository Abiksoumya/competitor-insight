# Task for review_agent# tasks/review_mining_task.py
# ─────────────────────────────────────────────────────
# Task template for review_agent.
# Mines G2 and Trustpilot for customer sentiment.
# ─────────────────────────────────────────────────────

from __future__ import annotations
from crewai  import Task
from agents.review_agent import review_agent
from shared.types        import CompanyName


def build_review_mining_task(company_name: CompanyName) -> Task:
    """
    Builds a configured review mining task for a specific company.

    Args:
        company_name: Company name to search reviews for

    Returns:
        Configured CrewAI Task assigned to review_agent
    """
    return Task(
        description=(
            f"Mine customer reviews for {company_name} from G2 "
            f"and Trustpilot.\n\n"

            f"INSTRUCTIONS:\n"
            f"1. Use the Review Scraper tool with '{company_name}'\n\n"

            f"2. Analyze all collected reviews carefully.\n"
            f"   Focus especially on NEGATIVE reviews — they reveal\n"
            f"   product gaps and competitive opportunities.\n\n"

            f"3. Look for PATTERNS not individual opinions:\n"
            f"   - If 5 people complain about the same thing → pattern\n"
            f"   - If 1 person complains → may be one-off\n\n"

            f"4. Categorize feedback into:\n"
            f"   - What customers consistently LOVE\n"
            f"   - What customers consistently COMPLAIN about\n"
            f"   - What features customers wish existed\n"
            f"   - What use cases customers mention most"
        ),

        expected_output=(
            "A structured customer sentiment report containing:\n\n"
            "1. OVERALL SENTIMENT\n"
            "   - Average rating if available\n"
            "   - General sentiment summary in 2-3 sentences\n\n"
            "2. WHAT CUSTOMERS LOVE (top 5 themes)\n"
            "   - Each theme with supporting evidence from reviews\n\n"
            "3. WHAT CUSTOMERS COMPLAIN ABOUT (top 5 themes)\n"
            "   - Each complaint with supporting evidence\n"
            "   - Why this is a competitive opportunity\n\n"
            "4. FEATURE REQUESTS\n"
            "   - Features customers wish the product had\n\n"
            "5. MOST COMMON USE CASES\n"
            "   - How customers actually use the product"
        ),

        agent=review_agent,
    )