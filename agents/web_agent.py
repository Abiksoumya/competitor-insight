# agents/web_agent.py

from __future__ import annotations
from crewai import Agent, LLM
from config.logging_config import get_logger
from config.settings       import settings
from tools.browser_tool    import scrape_page, scrape_multiple_pages, scrape_website

logger = get_logger(__name__)


def create_web_agent() -> Agent:
    logger.debug("Creating web_agent")

    # Tell CrewAI explicitly to use Claude — not OpenAI
    # Without this, CrewAI looks for OPENAI_API_KEY and crashes
    llm = LLM(
        model=settings.AGENT_LLM_MODEL,
        api_key=settings.AGENT_LLM_API_KEY,
    )

    return Agent(
        role="Senior Website Analyst",
        goal=(
            "Thoroughly analyze the competitor website to extract "
            "their complete product offering, pricing structure, "
            "key features, integrations, and positioning. "
            "Find the homepage, pricing page, and features page."
        ),
        backstory=(
            "You are a senior competitive intelligence specialist "
            "with 10 years of experience analyzing SaaS products. "
            "You have an eye for extracting structured product "
            "information from websites — pricing tiers, feature "
            "lists, target audiences, and unique selling points. "
            "You always visit multiple pages for a complete picture "
            "and never rely on just the homepage alone."
        ),
        tools=[scrape_page, scrape_multiple_pages, scrape_website],
        llm=llm,           # ← explicitly set Claude
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )


web_agent = create_web_agent()