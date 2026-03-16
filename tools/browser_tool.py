# tools/browser_tool.py
# ─────────────────────────────────────────────────────
# Playwright-based web scraper with smart page discovery.
# Used by: web_agent
#
# Why Playwright instead of requests + BeautifulSoup?
# Modern SaaS websites load content with JavaScript.
# requests only gets the raw HTML — JS hasn't run yet.
# Playwright launches a real browser, waits for JS to run,
# THEN reads the content. Gets what a real user would see.
#
# Smart scraping strategy:
# 1. Scrape homepage
# 2. Extract all internal links
# 3. Score links by competitive intelligence value
# 4. Scrape top 3 highest scoring pages
# Result: 4 pages of rich data instead of 1
# ─────────────────────────────────────────────────────

from __future__ import annotations
import asyncio
import re
from urllib.parse import urljoin, urlparse

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeout,
)
from bs4       import BeautifulSoup
from crewai.tools import tool

from config.settings       import settings
from config.logging_config import get_logger
from shared.types          import Url
from tools.config.tool_types import ScrapeResult

logger = get_logger(__name__)


# ── CORE PAGE SCRAPER ─────────────────────────────────────────────

async def _scrape_page_async(url: Url) -> ScrapeResult:
    """
    Internal async function that scrapes one page using Playwright.

    Args:
        url: The page URL to scrape

    Returns:
        ScrapeResult with clean text content or error details
    """
    logger.info("Scraping: %s", url)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            page = await browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )

            await page.goto(
                url,
                wait_until="networkidle",
                timeout=settings.SCRAPE_TIMEOUT * 1000,
            )

            html:  str = await page.content()
            title: str = await page.title()

            await browser.close()

            # ── CLEAN HTML ──────────────────────────────────
            soup = BeautifulSoup(html, "html.parser")

            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()

            content: str = soup.get_text(separator=" ", strip=True)
            content = re.sub(r"\s+", " ", content).strip()
            content = content[:8000]

            logger.info(
                "Scraped: %s — %d chars",
                url, len(content)
            )

            return ScrapeResult(
                url=url,
                content=content,
                title=title,
                success=True,
                error=None,
            )

    except PlaywrightTimeout:
        error_msg = f"Timed out after {settings.SCRAPE_TIMEOUT}s: {url}"
        logger.warning(error_msg)
        return ScrapeResult(
            url=url, content="", title="",
            success=False, error=error_msg,
        )

    except Exception as e:
        error_msg = f"Scrape failed for {url}: {str(e)}"
        logger.error(error_msg)
        return ScrapeResult(
            url=url, content="", title="",
            success=False, error=error_msg,
        )


# ── LINK DISCOVERY ────────────────────────────────────────────────

def _extract_internal_links(html: str, base_url: str) -> list[str]:
    """
    Extracts all internal links from a page's HTML.
    Internal = same domain as base_url.

    Args:
        html:     Raw HTML of the page
        base_url: Used to resolve relative URLs and filter external links

    Returns:
        Deduplicated list of absolute internal URLs
    """
    soup        = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(base_url).netloc
    # netloc extracts domain: "https://notion.so/pricing" → "notion.so"

    links: list[str] = []

    # With this
    for tag in soup.find_all("a", href=True):
        raw_href = tag.get("href")

        # Handle _AttributeValue — can be str or list[str]
        if isinstance(raw_href, list):
            raw_href = raw_href[0] if raw_href else ""

        href = str(raw_href).strip()

        # Skip empty, anchors, mailto, tel, javascript
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        # Convert relative to absolute URL
        absolute = urljoin(base_url, href)

        # Only keep same-domain links
        if urlparse(absolute).netloc == base_domain:
            links.append(absolute)

        # Skip anchors, mailto, tel, javascript
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        # Convert relative to absolute URL
        # "/pricing" + "https://notion.so" → "https://notion.so/pricing"
        absolute = urljoin(base_url, str(href))

        # Only keep same-domain links
        if urlparse(absolute).netloc == base_domain:
            links.append(absolute)

    # Deduplicate preserving order
    seen:   set[str]  = set()
    unique: list[str] = []
    for link in links:
        if link not in seen:
            seen.add(link)
            unique.append(link)

    return unique


def _score_page(url: str) -> int:
    """
    Scores a URL by competitive intelligence value.
    Higher score = more valuable to scrape.

    Scoring handles URL variations across different websites:
        /pricing, /plans, /price      → all score 10
        /features, /product           → all score 9

    Args:
        url: Page URL to score

    Returns:
        Integer score 1-10
    """
    url_lower = url.lower()

    score_map: list[tuple[int, list[str]]] = [
        (10, ["pricing", "price", "plans", "plan", "cost"]),
        (9,  ["features", "feature", "product", "platform"]),
        (8,  ["solution", "solutions", "use-case", "usecase"]),
        (6,  ["about", "company", "team", "story"]),
        (5,  ["integration", "integrations", "marketplace"]),
        (3,  ["blog", "resources", "docs", "documentation"]),
        (1,  ["careers", "jobs", "press", "legal", "privacy", "terms"]),
    ]

    for score, keywords in score_map:
        if any(kw in url_lower for kw in keywords):
            return score

    return 2  # default for unknown pages


async def _get_links_async(url: str) -> list[str]:
    """
    Extracts internal links from a page using Playwright.
    Separate from _scrape_page_async — only needs HTML for links,
    doesn't need cleaned text content.

    Args:
        url: Page URL to extract links from

    Returns:
        List of internal links found on the page
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page    = await browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            await page.goto(
                url,
                wait_until="networkidle",
                timeout=settings.SCRAPE_TIMEOUT * 1000,
            )
            html = await page.content()
            await browser.close()

            return _extract_internal_links(html, url)

    except Exception as e:
        logger.warning("Link extraction failed for %s: %s", url, str(e))
        return []


def _discover_key_pages(base_url: str, max_pages: int = 3) -> list[str]:
    """
    Discovers the most valuable pages on a competitor website.

    Strategy:
        1. Extract all internal links from homepage
        2. Score each link by competitive value
        3. Return top N pages by score

    Args:
        base_url:  Competitor homepage URL
        max_pages: Max pages to return — default 3

    Returns:
        List of top-scoring page URLs to scrape
    """
    logger.info("Discovering key pages on: %s", base_url)

    links = asyncio.run(_get_links_async(base_url))

    if not links:
        logger.warning("No internal links found on: %s", base_url)
        return []

    # Score and sort — highest value first
    scored: list[tuple[str, int]] = [
        (link, _score_page(link))
        for link in links
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Only return pages with score above noise threshold
    top_pages = [
        url for url, score in scored[:max_pages]
        if score > 2
    ]

    logger.info(
        "Discovered %d key pages: %s",
        len(top_pages), top_pages
    )

    return top_pages


# ── LOGIC FUNCTIONS ───────────────────────────────────────────────

def scrape_website_logic(url: str) -> str:
    """
    Smart multi-page scraper — discovers and scrapes key pages.

    Flow:
        1. Scrape homepage
        2. Discover top 3 valuable pages (pricing, features, about)
        3. Scrape each discovered page
        4. Combine all content into one rich output

    Args:
        url: Competitor homepage URL

    Returns:
        Combined content from homepage + top discovered pages
    """
    logger.info("Starting smart website scrape: %s", url)

    all_content: list[str] = []

    # ── STEP 1: Scrape homepage ────────────────────────
    home_result = asyncio.run(_scrape_page_async(url))

    if home_result["success"]:
        all_content.append(
            f"=== HOMEPAGE: {url} ===\n"
            f"Title: {home_result['title']}\n"
            f"{home_result['content']}\n"
        )
        logger.info(
            "Homepage scraped — %d chars",
            len(home_result["content"])
        )
    else:
        logger.warning("Homepage failed: %s", home_result["error"])

    # ── STEP 2: Discover key pages ─────────────────────
    key_pages = _discover_key_pages(url, max_pages=3)

    # ── STEP 3: Scrape each key page ──────────────────
    for page_url in key_pages:
        page_result = asyncio.run(_scrape_page_async(page_url))

        if page_result["success"]:
            all_content.append(
                f"=== {page_url} ===\n"
                f"Title: {page_result['title']}\n"
                f"{page_result['content']}\n"
            )
            logger.info(
                "Page scraped: %s — %d chars",
                page_url, len(page_result["content"])
            )
        else:
            logger.warning(
                "Page failed: %s — %s",
                page_url, page_result["error"]
            )

    if not all_content:
        return f"SCRAPE FAILED: Could not scrape any pages from {url}"

    logger.info(
        "Smart scrape complete — %d pages scraped",
        len(all_content)
    )

    return "\n\n".join(all_content)


def scrape_page_logic(url: str) -> str:
    """
    Scrapes a single page — fallback for specific URLs.

    Args:
        url: Exact URL to scrape

    Returns:
        Clean text content of the page
    """
    result: ScrapeResult = asyncio.run(_scrape_page_async(url))

    if result["success"]:
        return (
            f"PAGE TITLE: {result['title']}\n\n"
            f"CONTENT:\n{result['content']}"
        )
    return f"SCRAPE FAILED: {result['error']}"


def scrape_multiple_pages_logic(urls_comma_separated: str) -> str:
    """
    Scrapes multiple specific URLs and combines content.

    Args:
        urls_comma_separated: Comma-separated list of URLs

    Returns:
        Combined content from all pages
    """
    urls: list[str] = [
        u.strip()
        for u in urls_comma_separated.split(",")
        if u.strip()
    ]

    all_content: list[str] = []

    for url in urls[:4]:
        result: ScrapeResult = asyncio.run(_scrape_page_async(url))
        if result["success"]:
            all_content.append(
                f"=== {url} ===\n"
                f"Title: {result['title']}\n"
                f"{result['content']}\n"
            )
        else:
            all_content.append(
                f"=== {url} ===\n"
                f"FAILED: {result['error']}\n"
            )

    return "\n".join(all_content)


# ── CREWAI TOOLS ──────────────────────────────────────────────────

@tool("Smart Website Scraper")
def scrape_website(url: str) -> str:
    """
    Scrapes a competitor website intelligently.
    Automatically discovers and visits the most valuable pages:
    homepage, pricing page, features page, and about page.
    Use this as the PRIMARY tool for all website analysis.

    Args:
        url: Competitor homepage URL e.g. https://competitor.com

    Returns:
        Combined content from homepage and top discovered pages.
    """
    return scrape_website_logic(url)


@tool("Single Page Scraper")
def scrape_page(url: str) -> str:
    """
    Scrapes one specific page and returns its content.
    Use this when you need a specific page that was not
    automatically discovered by the smart scraper.

    Args:
        url: Exact URL to scrape e.g. https://competitor.com/pricing

    Returns:
        Clean text content of that specific page.
    """
    return scrape_page_logic(url)


@tool("Multi-Page Scraper")
def scrape_multiple_pages(urls_comma_separated: str) -> str:
    """
    Scrapes multiple specific pages and combines their content.
    Use this when you have a list of specific URLs to scrape.

    Args:
        urls_comma_separated: Comma-separated URLs
        e.g. "https://site.com/pricing, https://site.com/features"

    Returns:
        Combined content from all pages.
    """
    return scrape_multiple_pages_logic(urls_comma_separated)