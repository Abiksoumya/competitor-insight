# tools/review_scraper_tool.py
# ─────────────────────────────────────────────────────
# Scrapes customer reviews from G2 and Trustpilot.
# Used by: review_agent
#
# Strategy:
# 1. Try direct scraping of G2
# 2. If blocked or empty → fallback to Serper search snippets
# This is called "graceful degradation" — always return
# something useful even when the primary approach fails.
# ─────────────────────────────────────────────────────

from __future__ import annotations

import re
import httpx

from crewai.tools            import tool
from bs4                     import BeautifulSoup
from config.settings         import settings
from config.logging_config   import get_logger
from tools.config.tool_types import ReviewItem, ReviewScrapeResult
from tools.search_tool       import _call_serper

logger = get_logger(__name__)

# ── CONSTANTS ─────────────────────────────────────────────────────
# Headers that make our request look like a real browser.
# Review sites block requests without proper headers.
HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


# ── HELPERS ───────────────────────────────────────────────────────

def _get_rating(element) -> float:
    """
    Safely extracts a float rating from a BeautifulSoup element.

    Why this helper exists:
    BeautifulSoup attributes return _AttributeValue which is typed
    as str | list[str] | None. Passing that directly to float()
    causes a Pylance error AND a potential runtime crash if the
    value happens to be a list.

    This function handles every possible case explicitly:
        None        → 0.0
        list        → take first item, convert to float
        str         → convert directly to float
        invalid str → 0.0 (catches "N/A", "", etc.)

    Args:
        element: BeautifulSoup Tag or None

    Returns:
        float rating value, 0.0 if anything goes wrong
    """
    if not element:
        return 0.0

    # .get() is safer than element["content"]
    # Returns None if attribute is missing instead of raising KeyError
    raw = element.get("content")

    if raw is None:
        return 0.0

    # _AttributeValue can be a list[str] — take first item
    # Example: <div class="review active"> → class = ["review", "active"]
    if isinstance(raw, list):
        raw = raw[0] if raw else "0"

    # Now raw is guaranteed str — safe to convert
    try:
        return float(str(raw).strip())
    except (ValueError, TypeError):
        return 0.0


def _get_text_from_attr(element, attr: str = "content") -> str:
    """
    Safely extracts a string attribute from a BeautifulSoup element.

    Same problem as _get_rating — _AttributeValue can be list or str.
    This handles both cases and always returns a clean str.

    Args:
        element: BeautifulSoup Tag or None
        attr:    HTML attribute name to read — default "content"

    Returns:
        Attribute value as str, empty string if anything goes wrong
    """
    if not element:
        return ""

    raw = element.get(attr)

    if raw is None:
        return ""

    # Handle list case
    if isinstance(raw, list):
        raw = raw[0] if raw else ""

    return str(raw).strip()


# ── CORE SCRAPING FUNCTIONS ───────────────────────────────────────

def _scrape_g2(company_slug: str) -> list[ReviewItem]:
    """
    Attempts to scrape reviews directly from G2.

    G2 URL format:
        https://www.g2.com/products/{slug}/reviews

    G2 uses schema.org microdata markup — structured HTML attributes
    like itemprop="ratingValue" that make scraping more reliable.

    Args:
        company_slug: URL-safe company name e.g. "speel-ai"

    Returns:
        List of ReviewItem — empty list if scraping fails or blocked
    """
    url = f"https://www.g2.com/products/{company_slug}/reviews"
    logger.info("Scraping G2: %s", url)

    try:
        response = httpx.get(
            url,
            headers=HEADERS,
            timeout=15,
            follow_redirects=True,
            # follow_redirects=True handles cases where G2
            # redirects to a slightly different URL slug
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        reviews: list[ReviewItem] = []

        # G2 wraps each review in a div with itemprop="review"
        # This is schema.org structured markup — reliable to target
        review_elements = soup.find_all(
            "div", attrs={"itemprop": "review"}
        )

        logger.info(
            "Found %d review elements on G2",
            len(review_elements)
        )

        for el in review_elements[:settings.MAX_REVIEWS]:

            # ── RATING ──────────────────────────────────────
            # Use helper — handles _AttributeValue safely
            rating_el = el.find(attrs={"itemprop": "ratingValue"})
            rating: float = _get_rating(rating_el)

            # ── TITLE ───────────────────────────────────────
            title_el = el.find(attrs={"itemprop": "name"})
            title: str = (
                title_el.get_text(strip=True)
                if title_el else ""
            )

            # ── BODY ────────────────────────────────────────
            body_el = el.find(attrs={"itemprop": "reviewBody"})
            body: str = (
                body_el.get_text(strip=True)
                if body_el else ""
            )

            # ── DATE ────────────────────────────────────────
            # Use helper — handles _AttributeValue safely
            date_el = el.find(attrs={"itemprop": "datePublished"})
            date: str = _get_text_from_attr(date_el, "content")

            # Only add review if we actually got meaningful content
            if body:
                reviews.append(ReviewItem(
                    platform="g2",
                    rating=rating,
                    title=title,
                    body=body[:500],
                    # Truncate to 500 chars — prevents sending
                    # huge amounts of text to the agent
                    date=date,
                ))

        logger.info(
            "G2 scrape complete — collected %d reviews",
            len(reviews)
        )
        return reviews

    except httpx.HTTPStatusError as e:
        # G2 returned 4xx/5xx — likely blocked or slug is wrong
        logger.warning(
            "G2 HTTP error %d for slug '%s'",
            e.response.status_code,
            company_slug
        )
        return []

    except httpx.TimeoutException:
        logger.warning("G2 scrape timed out for slug: %s", company_slug)
        return []

    except Exception as e:
        logger.warning("G2 scrape failed: %s", str(e))
        return []
        # Return empty list — caller will trigger fallback


def _scrape_trustpilot(company_slug: str) -> list[ReviewItem]:
    """
    Attempts to scrape reviews directly from Trustpilot.

    Trustpilot URL format:
        https://www.trustpilot.com/review/{slug}

    Args:
        company_slug: Domain or slug e.g. "speel.ai"

    Returns:
        List of ReviewItem — empty list if scraping fails
    """
    url = f"https://www.trustpilot.com/review/{company_slug}"
    logger.info("Scraping Trustpilot: %s", url)

    try:
        response = httpx.get(
            url,
            headers=HEADERS,
            timeout=15,
            follow_redirects=True,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        reviews: list[ReviewItem] = []

        # Trustpilot also uses schema.org itemprop markup
        review_elements = soup.find_all(
            "article", attrs={"itemprop": "review"}
        )

        logger.info(
            "Found %d review elements on Trustpilot",
            len(review_elements)
        )

        for el in review_elements[:settings.MAX_REVIEWS]:

            # ── RATING ──────────────────────────────────────
            rating_el = el.find(attrs={"itemprop": "ratingValue"})
            rating: float = _get_rating(rating_el)

            # ── TITLE ───────────────────────────────────────
            title_el = el.find(attrs={"itemprop": "name"})
            title: str = (
                title_el.get_text(strip=True)
                if title_el else ""
            )

            # ── BODY ────────────────────────────────────────
            body_el = el.find(attrs={"itemprop": "reviewBody"})
            body: str = (
                body_el.get_text(strip=True)
                if body_el else ""
            )

            # ── DATE ────────────────────────────────────────
            date_el = el.find(attrs={"itemprop": "datePublished"})
            date: str = _get_text_from_attr(date_el, "content")

            if body:
                reviews.append(ReviewItem(
                    platform="trustpilot",
                    rating=rating,
                    title=title,
                    body=body[:500],
                    date=date,
                ))

        logger.info(
            "Trustpilot scrape complete — collected %d reviews",
            len(reviews)
        )
        return reviews

    except httpx.HTTPStatusError as e:
        logger.warning(
            "Trustpilot HTTP error %d for slug '%s'",
            e.response.status_code,
            company_slug
        )
        return []

    except httpx.TimeoutException:
        logger.warning(
            "Trustpilot timed out for slug: %s",
            company_slug
        )
        return []

    except Exception as e:
        logger.warning("Trustpilot scrape failed: %s", str(e))
        return []


def _search_reviews_fallback(company_name: str) -> list[ReviewItem]:
    """
    Fallback strategy when direct scraping is blocked.

    Uses Serper to search for reviews and builds ReviewItems
    from search result snippets. Not as detailed as direct
    scraping but always works — search is never blocked.

    This is "graceful degradation":
        Primary plan fails → fallback plan runs automatically
        User still gets useful data instead of an empty result

    Args:
        company_name: Company name e.g. "Speel AI"

    Returns:
        List of ReviewItem built from search snippets
    """
    logger.info(
        "Using search fallback for reviews: %s",
        company_name
    )

    # Multiple queries give broader coverage
    queries: list[str] = [
        f"{company_name} reviews G2",
        f"{company_name} customer reviews",
        f"{company_name} pros cons users",
        f"{company_name} trustpilot reviews",
    ]

    reviews: list[ReviewItem] = []

    for query in queries:
        response = _call_serper(query, num=5)

        if not response["success"]:
            logger.warning(
                "Search fallback query failed: %s",
                query
            )
            continue

        for result in response["results"]:
            snippet: str = result["snippet"].strip()
            if snippet:
                reviews.append(ReviewItem(
                    platform="g2",
                    # rating 0.0 = unknown from search snippet
                    rating=0.0,
                    title=result["title"],
                    body=snippet,
                    date="",
                ))

    logger.info(
        "Search fallback collected %d review snippets",
        len(reviews)
    )
    return reviews


def _format_reviews_for_agent(
    company_name: str,
    reviews:      list[ReviewItem],
) -> str:
    """
    Formats a list of ReviewItem into a readable string for agents.

    Agents receive and return plain strings — not Python objects.
    This function structures the reviews clearly so the agent
    can understand sentiment and identify patterns.

    Separates into:
        POSITIVE  → rating >= 4.0 or rating == 0.0 (unknown)
        NEGATIVE  → 0.0 < rating < 4.0

    Args:
        company_name: Used in the header
        reviews:      List of ReviewItem to format

    Returns:
        Formatted string with positive and negative sections
    """
    if not reviews:
        return f"No reviews found for {company_name}"

    # Separate by sentiment
    positive: list[ReviewItem] = [
        r for r in reviews
        if r["rating"] >= 4.0 or r["rating"] == 0.0
    ]
    negative: list[ReviewItem] = [
        r for r in reviews
        if 0.0 < r["rating"] < 4.0
    ]

    # Count rated reviews for average calculation
    rated: list[ReviewItem] = [
        r for r in reviews if r["rating"] > 0.0
    ]
    avg_rating: float = (
        sum(r["rating"] for r in rated) / len(rated)
        if rated else 0.0
    )

    lines: list[str] = [
        f"REVIEWS FOR: {company_name}",
        f"Total collected: {len(reviews)}",
        f"Average rating:  {avg_rating:.1f}/5.0\n",
        "── POSITIVE FEEDBACK ──────────────────────────",
    ]

    for r in positive[:15]:
        rating_str = f"[{r['rating']:.1f}★] " if r["rating"] > 0 else ""
        lines.append(f"• {rating_str}{r['title']}")
        lines.append(f"  {r['body'][:200]}\n")

    lines.append("── NEGATIVE FEEDBACK / COMPLAINTS ─────────────")

    if negative:
        for r in negative[:15]:
            lines.append(f"• [{r['rating']:.1f}★] {r['title']}")
            lines.append(f"  {r['body'][:200]}\n")
    else:
        lines.append("• No explicitly negative reviews found.")

    return "\n".join(lines)


# ── CREWAI TOOL ───────────────────────────────────────────────────

# Replace the @tool function at the bottom of review_scraper_tool.py

def scrape_reviews_logic(company_input: str) -> str:
    """Pure function — called directly in tests."""
    company_name: str = company_input.strip()
    company_slug: str = re.sub(
        r"[^a-z0-9]+", "-", company_name.lower()
    ).strip("-")

    logger.info(
        "Starting review scrape — name: '%s'  slug: '%s'",
        company_name, company_slug,
    )

    reviews: list[ReviewItem] = _scrape_g2(company_slug)

    if not reviews:
        logger.info("G2 empty — trying Trustpilot")
        reviews = _scrape_trustpilot(company_slug)

    if not reviews:
        logger.info("Both direct scrapes empty — using search fallback")
        reviews = _search_reviews_fallback(company_name)

    return _format_reviews_for_agent(company_name, reviews)


# ── CREWAI TOOL ───────────────────────────────────────────────────

@tool("Review Scraper")
def scrape_reviews(company_input: str) -> str:
    """
    Scrapes customer reviews for a company from G2 and Trustpilot.
    Returns what customers love and what they complain about.
    Use this to find competitor weaknesses and product gaps
    from real user feedback — not assumptions.

    Args:
        company_input: Company name or domain
        e.g. "Speel AI" or "speel.ai"

    Returns:
        Formatted review summary split into positive feedback
        and complaints, with ratings where available.
    """
    return scrape_reviews_logic(company_input)