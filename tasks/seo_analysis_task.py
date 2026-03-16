# Task for seo_agent# tasks/seo_analysis_task.py
# ─────────────────────────────────────────────────────
# Task template for seo_agent.
# Reverse-engineers competitor SEO and content strategy.
# ─────────────────────────────────────────────────────

from __future__ import annotations
import re
from crewai   import Task
from agents.seo_agent import seo_agent
from shared.types     import Url, CompanyName


def build_seo_analysis_task(url: Url, company_name: CompanyName) -> Task:
    """
    Builds a configured SEO analysis task.

    Args:
        url:          Competitor URL for domain extraction
        company_name: Company name for search queries

    Returns:
        Configured CrewAI Task assigned to seo_agent
    """
    # Extract clean domain from URL
    # "https://www.notion.so/pricing" → "notion.so"
    domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]

    return Task(
        description=(
            f"Analyze the SEO and content strategy for "
            f"{company_name} at domain {domain}.\n\n"

            f"INSTRUCTIONS:\n"
            f"1. Use SEO Keyword Search tool with '{domain}'\n"
            f"   to find their indexed pages and keywords.\n\n"

            f"2. Search for their content themes:\n"
            f"   '{company_name} blog topics'\n"
            f"   '{company_name} use cases guide'\n\n"

            f"3. Search for what their audience wants:\n"
            f"   'best {company_name} alternatives'\n"
            f"   '{company_name} vs competitors'\n"
            f"   '{company_name} missing features'\n\n"

            f"4. Identify content gaps:\n"
            f"   Topics their audience searches for but\n"
            f"   they don't have good content covering.\n\n"

            f"5. Estimate posting frequency from:\n"
            f"   Number of blog posts visible in search results\n"
            f"   Dates visible on search result snippets."
        ),

        expected_output=(
            "An SEO and content strategy report containing:\n\n"
            "1. PRIMARY KEYWORDS\n"
            "   - Top 10 keywords they appear to target\n"
            "   - Their estimated search intent for each\n\n"
            "2. CONTENT THEMES\n"
            "   - Main topics they publish content about\n"
            "   - Content formats they use (guides, tutorials, etc)\n\n"
            "3. PUBLISHING CADENCE\n"
            "   - Estimated posting frequency\n"
            "   - Content volume assessment\n\n"
            "4. TARGET AUDIENCE SIGNALS\n"
            "   - Who their content targets based on topics\n"
            "   - Pain points they address in content\n\n"
            "5. CONTENT GAPS\n"
            "   - Top 5 topics their audience wants\n"
            "     but they don't cover well\n"
            "   - Each gap is a content opportunity for you"
        ),

        agent=seo_agent,
    )