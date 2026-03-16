# tools/config/tool_types.py
# ─────────────────────────────────────────────────────
# Types used only inside the tools/ folder.
# Agents import ScrapeResult and SearchResult to read
# tool outputs — but they import from here, not from tools/
# ─────────────────────────────────────────────────────

from __future__ import annotations
from typing  import TypedDict, Optional, Literal
from shared.types import Url


# Which review platforms we support scraping
ReviewPlatform = Literal["g2", "trustpilot", "product_hunt"]


class ScrapeResult(TypedDict):
    """
    Result from browser_tool.py after scraping one page.

    success=True  → content has the page text
    success=False → content is empty, error explains why

    Why include both success flag AND error string?
    Because agents need to handle partial failures gracefully.
    If web scraping fails, the agent should log the error
    and continue with whatever data it has — not crash.
    """
    url:         Url
    content:     str            # Cleaned page text — HTML tags removed
    title:       str            # Page <title> tag content
    success:     bool
    error:       Optional[str]  # None if success=True


class SearchResult(TypedDict):
    """
    One search result item from Serper API.
    news_agent and seo_agent get a list of these.
    """
    title:    str
    url:      Url
    snippet:  str    # Short description from Google search result


class SearchResponse(TypedDict):
    """
    Full response from search_tool.py after one search query.
    Contains a list of SearchResult items.
    """
    query:    str
    results:  list[SearchResult]
    success:  bool
    error:    Optional[str]


class ReviewItem(TypedDict):
    """
    One individual customer review scraped from G2 or Trustpilot.
    review_scraper_tool.py returns a list of these.
    """
    platform:   ReviewPlatform
    rating:     float           # 1.0 to 5.0
    title:      str             # Review headline
    body:       str             # Full review text
    date:       str             # When review was posted


class ReviewScrapeResult(TypedDict):
    """
    Full result from review_scraper_tool.py.
    Contains all reviews collected across platforms.
    """
    company:    str
    reviews:    list[ReviewItem]
    total:      int             # Total reviews collected
    success:    bool
    error:      Optional[str]