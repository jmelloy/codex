"""Open Graph metadata scraper.

This module provides functionality to fetch and parse Open Graph metadata from web pages.
"""

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OpenGraphScraper:
    """Scraper for extracting Open Graph metadata from web pages."""

    def __init__(self, timeout: int = 10):
        """Initialize scraper.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

    async def scrape_url(self, url: str) -> dict[str, Any]:
        """Scrape Open Graph metadata from a URL.

        Args:
            url: URL to scrape

        Returns:
            Dictionary containing Open Graph metadata

        Raises:
            httpx.HTTPError: If the request fails
            ValueError: If URL is invalid
        """
        if not url or not url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL: {url}")

        logger.info(f"Scraping Open Graph metadata from: {url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Codex Link Unfurl Bot/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            html = response.text

        # Parse Open Graph tags
        metadata = self._parse_og_tags(html)

        # Add the requested URL if not present
        if "url" not in metadata:
            metadata["url"] = url

        # Use page title as fallback for og:title
        if "title" not in metadata:
            title = self._extract_title(html)
            if title:
                metadata["title"] = title

        return metadata

    def _parse_og_tags(self, html: str) -> dict[str, str]:
        """Parse Open Graph meta tags from HTML.

        Args:
            html: HTML content

        Returns:
            Dictionary of Open Graph properties
        """
        metadata = {}

        # Pattern to match Open Graph meta tags
        # Examples:
        # <meta property="og:title" content="Page Title">
        # <meta property="og:image" content="https://example.com/image.jpg">
        # Handles attributes in any order and additional attributes between property and content
        og_pattern = re.compile(
            r'<meta\s+[^>]*property=["\']og:([^"\']+)["\'][^>]*content=["\']([^"\']+)["\'][^>]*>',
            re.IGNORECASE,
        )

        # Also match reverse order (content before property)
        og_pattern_reverse = re.compile(
            r'<meta\s+[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:([^"\']+)["\'][^>]*>',
            re.IGNORECASE,
        )

        for match in og_pattern.finditer(html):
            prop = match.group(1)
            content = match.group(2)
            metadata[prop] = content

        for match in og_pattern_reverse.finditer(html):
            content = match.group(1)
            prop = match.group(2)
            metadata[prop] = content

        return metadata

    def _extract_title(self, html: str) -> str | None:
        """Extract page title as fallback.

        Args:
            html: HTML content

        Returns:
            Page title or None if not found
        """
        title_match = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()
        return None
