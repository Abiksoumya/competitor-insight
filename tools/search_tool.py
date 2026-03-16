# Serper API web search# tools/search_tool.py
# ─────────────────────────────────────────────────────
# Serper API wrapper — gives agents Google Search access.
# Used by: news_agent (recent news), seo_agent (keywords)
#
# Why Serper and not Google directly?
# Google's official API is complex and expensive.
# Serper is a thin wrapper around Google Search —
# simple REST API, 2500 free searches/month, instant setup.
#
# What is an API wrapper?
# A function that takes simple inputs, calls an external
# API for you, and returns clean structured output.
# The agent doesn't know or care about HTTP — it just
# calls web_search("query") and gets results back.
# ─────────────────────────────────────────────────────

from __future__ import annotations
import httpx
# httpx is a modern HTTP client — like requests but supports async
# We use it synchronously here since @tool must be sync

from crewai.tools import tool
from config.settings       import settings
from config.logging_config import get_logger
from shared.types           import Url
from tools.config.tool_types import SearchResult, SearchResponse

logger = get_logger(__name__)

# Serper API endpoint — all searches go through this URL
SERPER_URL = "https://google.serper.dev/search"


def _call_serper(
    query:    str,
    num:      int = 10,
    time_range: str | None = None,
) -> SearchResponse:
    """
    Internal function that calls the Serper API.
    Not exposed as a tool — used by the public tool functions below.

    Args:
        query:      Search query string
        num:        Number of results to return (max 10)
        time_range: Restrict results by time — "qdr:m" = past month,
                    "qdr:y" = past year, None = any time

    Returns:
        SearchResponse with list of results or error details
    """
    logger.info("Searching: '%s' (n=%d)", query, num)

    try:
        # Build request payload
        payload: dict = {
            "q": query,     # The search query
            "num": num,     # How many results to return
        }
        if time_range:
            payload["tbs"] = time_range
            # tbs = "time-based search" — Serper/Google parameter

        # Make the HTTP request to Serper
        # timeout=10 means give up after 10 seconds
        response = httpx.post(
            url=SERPER_URL,
            headers={
                "X-API-KEY": settings.SERPER_API_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )

        # Raise an exception if status code is 4xx or 5xx
        # This is the "fail fast" principle — don't silently
        # return empty results when something went wrong
        response.raise_for_status()

        data: dict = response.json()

        # ── PARSE RESULTS ───────────────────────────────
        # Serper returns results in "organic" key
        # Each result has: title, link, snippet
        raw_results: list[dict] = data.get("organic", [])

        results: list[SearchResult] = [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("link", ""),
                snippet=r.get("snippet", ""),
            )
            for r in raw_results
        ]

        logger.info("Search returned %d results", len(results))

        return SearchResponse(
            query=query,
            results=results,
            success=True,
            error=None,
        )

    except httpx.HTTPStatusError as e:
        # Serper returned 4xx/5xx — API key wrong, quota exceeded etc.
        error_msg = f"Serper API error {e.response.status_code}: {str(e)}"
        logger.error(error_msg)
        return SearchResponse(
            query=query, results=[],
            success=False, error=error_msg
        )

    except Exception as e:
        error_msg = f"Search failed for '{query}': {str(e)}"
        logger.error(error_msg)
        return SearchResponse(
            query=query, results=[],
            success=False, error=error_msg
        )


def _format_results(response: SearchResponse) -> str:
    """
    Converts SearchResponse into a readable string for agents.
    Agents receive strings — not Python objects.
    This formats the results clearly so the agent can read them.
    """
    if not response["success"]:
        return f"SEARCH FAILED: {response['error']}"

    if not response["results"]:
        return f"No results found for: {response['query']}"

    lines: list[str] = [
        f"SEARCH RESULTS FOR: {response['query']}\n"
    ]

    for i, result in enumerate(response["results"], start=1):
        lines.append(
            f"{i}. {result['title']}\n"
            f"   URL: {result['url']}\n"
            f"   {result['snippet']}\n"
        )

    return "\n".join(lines)


# Replace the @tool functions at the bottom of search_tool.py

def web_search_logic(query: str) -> str:
    """Pure function — called directly in tests."""
    response = _call_serper(query, num=10)
    return _format_results(response)


def search_recent_news_logic(query: str) -> str:
    """Pure function — called directly in tests."""
    response = _call_serper(query, num=10, time_range="qdr:m")
    return _format_results(response)


def search_seo_keywords_logic(company_domain: str) -> str:
    """Pure function — called directly in tests."""
    queries: list[str] = [
        f"site:{company_domain}",
        f"{company_domain} features pricing",
        f"{company_domain} blog tutorial",
    ]
    all_results: list[str] = []
    for q in queries:
        response = _call_serper(q, num=5)
        all_results.append(_format_results(response))
    return "\n\n".join(all_results)


# ── CREWAI TOOLS ──────────────────────────────────────────────────

@tool("Web Search")
def web_search(query: str) -> str:
    """
    Searches the web using Google and returns top results.
    Use this to find information about a company, their news,
    recent announcements, or any topic that needs current data.

    Args:
        query: Search query e.g. "Speel AI funding 2024"

    Returns:
        Numbered list of search results with titles,
        URLs, and descriptions.
    """
    return web_search_logic(query)


@tool("Recent News Search")
def search_recent_news(query: str) -> str:
    """
    Searches for news from the past month only.
    Use this when you need recent funding announcements,
    product launches, or press coverage about a company.

    Args:
        query: Search query e.g. "Speel AI product launch"

    Returns:
        Recent news results from the past month.
    """
    return search_recent_news_logic(query)


@tool("SEO Keyword Search")
def search_seo_keywords(company_domain: str) -> str:
    """
    Finds SEO keywords and content topics a company targets.
    Use this to understand a competitor's content strategy.

    Args:
        company_domain: Domain name e.g. "speel.ai"

    Returns:
        Search results showing their content and keyword themes.
    """
    return search_seo_keywords_logic(company_domain)