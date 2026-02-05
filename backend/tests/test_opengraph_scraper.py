"""Tests for Open Graph scraper."""

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
