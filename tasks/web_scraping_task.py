# Task for web_agent# tasks/web_scraping_task.py
# ─────────────────────────────────────────────────────
# Task template for web_agent.
# Defines WHAT the agent should do and WHAT it should return.
#
# Relationship:
#   web_scraping_task.py  → defines the task template
#   crew_runner.py        → calls build_web_scraping_task(url)
#                           to get a configured Task instance
#   web_agent             → executes the task
# ─────────────────────────────────────────────────────

from __future__ import annotations
from crewai  import Task
from agents.web_agent import web_agent
from shared.types     import Url


def build_web_scraping_task(url: Url) -> Task:
    """
    Builds a configured web scraping task for a specific URL.

    Why a function instead of a module-level Task instance?
    Tasks need the competitor URL baked into their description.
    Each job has a different URL — so we build fresh each time.
    Module-level instances would reuse the same URL forever.

    Args:
        url: Competitor homepage URL to scrape

    Returns:
        Configured CrewAI Task assigned to web_agent
    """
    return Task(
        description=(
            f"Scrape the competitor website at {url}.\n\n"

            f"INSTRUCTIONS:\n"
            f"1. Use the Smart Website Scraper tool with {url}\n"
            f"   It will automatically find and scrape the homepage,\n"
            f"   pricing page, features page, and about page.\n\n"

            f"2. If any important page is missing from the results,\n"
            f"   use the Single Page Scraper to get it directly.\n\n"

            f"3. Extract and structure the following information:\n"
            f"   - Product name and main tagline\n"
            f"   - Core value proposition (what problem does it solve?)\n"
            f"   - Key features list (at least 5 if visible)\n"
            f"   - All pricing tiers (name, price, what is included)\n"
            f"   - Free trial or freemium offering if any\n"
            f"   - Integrations and tech stack signals\n"
            f"   - Target customer and use cases\n\n"

            f"4. If a page fails to load, continue with other pages.\n"
            f"   Partial data is better than no data."
        ),

        expected_output=(
            "A structured website analysis report containing:\n"
            "1. PRODUCT OVERVIEW\n"
            "   - Product name and tagline\n"
            "   - Core value proposition\n"
            "   - Target customer segment\n\n"
            "2. KEY FEATURES\n"
            "   - Feature list with brief description of each\n\n"
            "3. PRICING\n"
            "   - Each pricing tier: name, price, what is included\n"
            "   - Free trial / freemium details if available\n\n"
            "4. INTEGRATIONS & TECH STACK\n"
            "   - Integration partners mentioned\n"
            "   - Tech stack clues if visible\n\n"
            "5. TARGET AUDIENCE\n"
            "   - Who they are targeting based on messaging"
        ),

        agent=web_agent,
    )