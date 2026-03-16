from __future__ import annotations
from crewai import Agent, LLM
from config.logging_config     import get_logger
from config.settings           import settings
from tools.review_scraper_tool import scrape_reviews

logger = get_logger(__name__)


def create_review_agent() -> Agent:
    logger.debug("Creating review_agent")

    llm = LLM(
        model=settings.AGENT_LLM_MODEL,
        api_key=settings.AGENT_LLM_API_KEY,
    )

    return Agent(
        role="Customer Sentiment Analyst",
        goal=(
            "Mine customer reviews from G2 and Trustpilot to "
            "identify what users genuinely love about the competitor "
            "product and — more importantly — what they complain "
            "about. Complaints reveal product gaps and your "
            "competitive opportunities."
        ),
        backstory=(
            "You are an expert in voice-of-customer research with "
            "8 years analyzing product reviews for Fortune 500 "
            "companies. You excel at identifying patterns in customer "
            "feedback — separating surface complaints from deep "
            "structural product weaknesses. You know that a product's "
            "negative reviews are worth 10x more than its positive "
            "ones for competitive strategy. You always look for "
            "recurring themes, not one-off complaints."
        ),
        tools=[scrape_reviews],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )


review_agent = create_review_agent()