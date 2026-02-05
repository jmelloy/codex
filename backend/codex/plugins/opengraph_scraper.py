"""Open Graph metadata scraper.

This module provides functionality to fetch and parse Open Graph metadata from web pages.
"""

import logging
import os
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
        self.opengraph_io_api_key = os.getenv("OPENGRAPH_IO_API_KEY")

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

        try:
            # Try direct scraping first
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

        except Exception as e:
            # If direct scraping fails and we have an API key, try opengraph.io fallback
            if self.opengraph_io_api_key:
                logger.warning(f"Direct scraping failed for {url}, trying opengraph.io fallback: {e}")
                return await self._scrape_with_opengraph_io(url)
            else:
                # No fallback available, re-raise the original exception
                logger.error(f"Direct scraping failed for {url} and no fallback API key configured: {e}")
                raise

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

    async def _scrape_with_opengraph_io(self, url: str) -> dict[str, Any]:
        """Scrape Open Graph metadata using opengraph.io API.

        Args:
            url: URL to scrape

        Returns:
            Dictionary containing Open Graph metadata

        Raises:
            httpx.HTTPError: If the API request fails
        """
        logger.info(f"Fetching Open Graph metadata from opengraph.io API for: {url}")

        api_url = "https://opengraph.io/api/1.1/site"
        params = {
            "app_id": self.opengraph_io_api_key,
            "url": url,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(api_url, params=params)
            response.raise_for_status()
            data = response.json()

        # Transform opengraph.io response to our format
        # The API returns data in format: {"hybridGraph": {"title": ..., "description": ..., "image": ...}}
        metadata = {}

        if "hybridGraph" in data:
            hybrid = data["hybridGraph"]

            # Map common fields
            if "title" in hybrid:
                metadata["title"] = hybrid["title"]
            if "description" in hybrid:
                metadata["description"] = hybrid["description"]
            if "image" in hybrid:
                metadata["image"] = hybrid["image"]
            if "url" in hybrid:
                metadata["url"] = hybrid["url"]
            elif "site" in hybrid:
                metadata["url"] = hybrid["site"]
            if "site_name" in hybrid:
                metadata["site_name"] = hybrid["site_name"]

            # Also check openGraph nested object for more complete data
            if "openGraph" in data:
                og = data["openGraph"]
                # Override with OpenGraph data if available
                if "title" in og:
                    metadata["title"] = og["title"]
                if "description" in og:
                    metadata["description"] = og["description"]
                if "image" in og:
                    # OpenGraph image can be an array or object
                    if isinstance(og["image"], list) and len(og["image"]) > 0:
                        metadata["image"] = og["image"][0].get("url") if isinstance(og["image"][0], dict) else og["image"][0]
                    elif isinstance(og["image"], dict):
                        metadata["image"] = og["image"].get("url")
                    else:
                        metadata["image"] = og["image"]
                if "url" in og:
                    metadata["url"] = og["url"]
                if "siteName" in og:
                    metadata["site_name"] = og["siteName"]

        # Ensure URL is set
        if "url" not in metadata:
            metadata["url"] = url

        return metadata
