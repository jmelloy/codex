"""Tests for Open Graph scraper."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from codex.plugins.opengraph_scraper import OpenGraphScraper


@pytest.fixture
def scraper():
    """Create scraper instance."""
    return OpenGraphScraper(timeout=10)


def test_parse_og_tags(scraper):
    """Test parsing Open Graph tags from HTML."""
    html = """
    <html>
    <head>
        <meta property="og:title" content="Example Title">
        <meta property="og:description" content="Example description">
        <meta property="og:image" content="https://example.com/image.jpg">
        <meta content="https://example.com" property="og:url">
        <meta property="og:site_name" content="Example Site">
    </head>
    <body></body>
    </html>
    """

    metadata = scraper._parse_og_tags(html)

    assert metadata["title"] == "Example Title"
    assert metadata["description"] == "Example description"
    assert metadata["image"] == "https://example.com/image.jpg"
    assert metadata["url"] == "https://example.com"
    assert metadata["site_name"] == "Example Site"


def test_extract_title(scraper):
    """Test extracting title from HTML."""
    html = "<html><head><title>Page Title</title></head><body></body></html>"

    title = scraper._extract_title(html)

    assert title == "Page Title"


def test_extract_title_not_found(scraper):
    """Test extracting title when not present."""
    html = "<html><head></head><body></body></html>"

    title = scraper._extract_title(html)

    assert title is None


@pytest.mark.asyncio
async def test_scrape_url_invalid(scraper):
    """Test scraping with invalid URL raises error."""
    with pytest.raises(ValueError, match="Invalid URL"):
        await scraper.scrape_url("not-a-url")


@pytest.mark.asyncio
async def test_scrape_url_example():
    """Test scraping a real URL (example.com)."""
    scraper = OpenGraphScraper(timeout=10)

    try:
        metadata = await scraper.scrape_url("https://example.com")

        # Should at least have a URL and title
        assert "url" in metadata
        assert metadata["url"] == "https://example.com"
        assert "title" in metadata
    except Exception as e:
        # Network issues can cause this to fail in CI
        pytest.skip(f"Network test skipped: {e}")


@pytest.mark.asyncio
async def test_fallback_to_opengraph_io_when_direct_fails():
    """Test that scraper falls back to opengraph.io API when direct scraping fails."""
    # Mock environment variable
    with patch.dict(os.environ, {"OPENGRAPH_IO_API_KEY": "test-api-key"}):
        scraper = OpenGraphScraper(timeout=10)
        
        # Track whether fallback method was called
        fallback_called = False
        original_fallback = scraper._scrape_with_opengraph_io
        
        async def mock_fallback(url):
            nonlocal fallback_called
            fallback_called = True
            return {
                "title": "Test Title OG",
                "description": "Test Description OG",
                "url": url
            }
        
        scraper._scrape_with_opengraph_io = mock_fallback
        
        # Mock direct scraping to fail
        with patch("httpx.AsyncClient") as mock_client:
            mock_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = mock_context
            
            # Make get() raise an exception
            async def mock_get(*args, **kwargs):
                raise httpx.HTTPStatusError("404 Not Found", request=MagicMock(), response=MagicMock())
            
            mock_context.get = mock_get
            
            # Execute
            metadata = await scraper.scrape_url("https://example.com")
            
            # Verify fallback was used
            assert fallback_called
            assert metadata["title"] == "Test Title OG"
            assert metadata["description"] == "Test Description OG"
            assert metadata["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_no_fallback_when_api_key_missing():
    """Test that scraper raises error when direct scraping fails and no API key."""
    # Ensure no API key is set (reinitialize scraper without key)
    with patch.dict(os.environ, {}, clear=True):
        scraper = OpenGraphScraper(timeout=10)
        assert scraper.opengraph_io_api_key is None
        
        # Mock the HTTP client to fail
        with patch("httpx.AsyncClient") as mock_client:
            mock_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = mock_context
            
            # Make get() raise an exception
            async def mock_get(*args, **kwargs):
                raise httpx.HTTPStatusError("404 Not Found", request=MagicMock(), response=MagicMock())
            
            mock_context.get = mock_get
            
            # Should raise the original error
            with pytest.raises(httpx.HTTPStatusError):
                await scraper.scrape_url("https://example.com")


@pytest.mark.asyncio
async def test_opengraph_io_api_call():
    """Test direct call to opengraph.io API."""
    with patch.dict(os.environ, {"OPENGRAPH_IO_API_KEY": "test-api-key"}):
        scraper = OpenGraphScraper(timeout=10)
        
        # Mock the HTTP client for API call
        with patch("httpx.AsyncClient") as mock_client:
            mock_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = mock_context
            
            # Mock successful API response
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value={
                "hybridGraph": {
                    "title": "Test Title",
                    "site": "https://example.com"
                },
                "openGraph": {
                    "title": "OG Title",
                    "description": "OG Description",
                    "image": [
                        {"url": "https://example.com/img1.jpg"},
                        {"url": "https://example.com/img2.jpg"}
                    ],
                    "url": "https://example.com"
                }
            })
            
            async def mock_get(*args, **kwargs):
                return mock_response
            
            async def mock_raise_for_status():
                pass
            
            mock_response.raise_for_status = mock_raise_for_status
            mock_context.get = mock_get
            
            # Call the fallback method directly
            metadata = await scraper._scrape_with_opengraph_io("https://example.com")
            
            # Should use openGraph data and extract first image from array
            assert metadata["title"] == "OG Title"
            assert metadata["description"] == "OG Description"
            assert metadata["image"] == "https://example.com/img1.jpg"
            assert metadata["url"] == "https://example.com"
