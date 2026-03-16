from __future__ import annotations
from crewai import Agent, LLM
from config.logging_config import get_logger
from config.settings       import settings
from tools.search_tool     import web_search, search_recent_news

logger = get_logger(__name__)


def create_news_agent() -> Agent:
    logger.debug("Creating news_agent")

    llm = LLM(
        model=settings.AGENT_LLM_MODEL,
        api_key=settings.AGENT_LLM_API_KEY,
    )

    return Agent(
        role="Business Intelligence Researcher",
        goal=(
            "Research recent news, funding rounds, product launches, "
            "and hiring trends for the competitor company. "
            "Focus on the last 6 months. Identify signals that "
            "reveal what they are building next and where they "
            "are investing resources."
        ),
        backstory=(
            "You are a business intelligence researcher with a "
            "background in venture capital and tech journalism. "
            "You know how to read between the lines — a job posting "
            "for ML engineers signals an AI product in development, "
            "a Series B funding round signals aggressive expansion. "
            "You always search for multiple angles: official press "
            "releases, tech news coverage, LinkedIn announcements, "
            "and investor updates. You never rely on a single source."
        ),
        tools=[web_search, search_recent_news],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=4,
    )


news_agent = create_news_agent()