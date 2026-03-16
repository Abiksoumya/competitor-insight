from __future__ import annotations
from crewai import Agent, LLM
from config.logging_config import get_logger
from config.settings       import settings
from tools.search_tool     import web_search, search_seo_keywords

logger = get_logger(__name__)


def create_seo_agent() -> Agent:
    logger.debug("Creating seo_agent")

    llm = LLM(
        model=settings.AGENT_LLM_MODEL,
        api_key=settings.AGENT_LLM_API_KEY,
    )

    return Agent(
        role="SEO and Content Strategy Analyst",
        goal=(
            "Reverse-engineer the competitor's SEO and content "
            "strategy. Find which keywords they rank for, what "
            "topics they publish content about, how frequently "
            "they post, and — most valuably — what content gaps "
            "exist that their audience wants but they don't cover."
        ),
        backstory=(
            "You are a senior SEO strategist who has helped 50+ "
            "SaaS companies grow organic traffic from zero to "
            "millions of monthly visitors. You can reverse-engineer "
            "any competitor's content strategy from their public "
            "footprint alone. You know that content gaps are "
            "golden opportunities — topics an audience searches "
            "for but no competitor covers well yet. You always "
            "look at both their blog content AND their product "
            "pages for SEO signals."
        ),
        tools=[web_search, search_seo_keywords],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=4,
    )


seo_agent = create_seo_agent()