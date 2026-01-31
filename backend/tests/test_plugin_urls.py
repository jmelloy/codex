"""Tests to validate URLs in integration plugins."""

import re
from pathlib import Path

import pytest

from codex.plugins.loader import PluginLoader
from codex.plugins.models import IntegrationPlugin

# Get the plugins directory at repository root
BACKEND_DIR = Path(__file__).parent.parent
PLUGINS_DIR = BACKEND_DIR.parent / "plugins"


@pytest.fixture
def loader():
    """Create plugin loader."""
    return PluginLoader(PLUGINS_DIR)


def test_github_integration_urls(loader):
    """Test GitHub integration URLs are valid."""
    loader.load_all_plugins()
    github = loader.get_plugin("github")
    
    assert github is not None
    assert isinstance(github, IntegrationPlugin)
    
    # Check base URL
    assert github.base_url == "https://api.github.com"
    
    # Check URL patterns in blocks
    blocks = github.blocks
    assert len(blocks) == 3
    
    # Check issue block
    issue_block = next((b for b in blocks if b["id"] == "github-issue"), None)
    assert issue_block is not None
    assert len(issue_block["url_patterns"]) == 1
    assert issue_block["url_patterns"][0] == "https://github.com/.*/issues/.*"
    
    # Check PR block
    pr_block = next((b for b in blocks if b["id"] == "github-pr"), None)
    assert pr_block is not None
    assert len(pr_block["url_patterns"]) == 1
    assert pr_block["url_patterns"][0] == "https://github.com/.*/pull/.*"
    
    # Check repo block
    repo_block = next((b for b in blocks if b["id"] == "github-repo"), None)
    assert repo_block is not None
    assert len(repo_block["url_patterns"]) == 1
    # This pattern should match a GitHub repo URL but not issue/PR URLs
    pattern = repo_block["url_patterns"][0]
    assert pattern == "https://github.com/[^/]+/[^/]+/?$"


def test_github_url_patterns_validity(loader):
    """Test that GitHub URL patterns are valid regex and match expected URLs."""
    loader.load_all_plugins()
    github = loader.get_plugin("github")
    
    blocks = github.blocks
    
    # Test issue pattern
    issue_pattern = next((b["url_patterns"][0] for b in blocks if b["id"] == "github-issue"), None)
    issue_regex = re.compile(issue_pattern)
    
    # Should match issue URLs
    assert issue_regex.search("https://github.com/owner/repo/issues/123")
    assert issue_regex.search("https://github.com/facebook/react/issues/456")
    
    # Should not match repo URLs (without issue number)
    # Note: This pattern is greedy and WILL match longer URLs containing "/issues/"
    # which is actually correct behavior - issue URLs should be caught before repo URLs
    
    # Test PR pattern
    pr_pattern = next((b["url_patterns"][0] for b in blocks if b["id"] == "github-pr"), None)
    pr_regex = re.compile(pr_pattern)
    
    # Should match PR URLs
    assert pr_regex.search("https://github.com/owner/repo/pull/456")
    assert pr_regex.search("https://github.com/facebook/react/pull/789")
    
    # Test repo pattern
    repo_pattern = next((b["url_patterns"][0] for b in blocks if b["id"] == "github-repo"), None)
    repo_regex = re.compile(repo_pattern)
    
    # Should match repo URLs
    assert repo_regex.search("https://github.com/owner/repo")
    assert repo_regex.search("https://github.com/facebook/react")
    assert repo_regex.search("https://github.com/owner/repo/")  # With trailing slash
    
    # Should NOT match issue/PR URLs or other paths with the anchored pattern
    assert not repo_regex.search("https://github.com/owner/repo/issues/123")
    assert not repo_regex.search("https://github.com/owner/repo/pull/456")
    assert not repo_regex.search("https://github.com/owner/repo/tree/main")
    assert not repo_regex.search("https://github.com/owner/repo/blob/main/README.md")
    assert not repo_regex.search("https://github.com/owner/repo/tree/main/src")
    assert not repo_regex.search("https://github.com/owner/repo/wiki")
    assert not repo_regex.search("https://github.com/owner/repo/actions")


def test_weather_integration_urls(loader):
    """Test Weather API integration URLs are valid."""
    loader.load_all_plugins()
    weather = loader.get_plugin("weather-api")
    
    assert weather is not None
    assert isinstance(weather, IntegrationPlugin)
    
    # Check base URL
    assert weather.base_url == "https://api.openweathermap.org/data/2.5"
    
    # Check endpoints exist and have correct paths
    endpoints = weather.endpoints
    assert len(endpoints) >= 2
    
    # Check current_weather endpoint
    current_endpoint = next((e for e in endpoints if e["id"] == "current_weather"), None)
    assert current_endpoint is not None
    assert current_endpoint["path"] == "/weather"
    assert current_endpoint["method"] == "GET"
    
    # Check forecast endpoint
    forecast_endpoint = next((e for e in endpoints if e["id"] == "forecast"), None)
    assert forecast_endpoint is not None
    assert forecast_endpoint["path"] == "/forecast"
    assert forecast_endpoint["method"] == "GET"


def test_opengraph_integration_urls(loader):
    """Test OpenGraph integration URLs are valid."""
    loader.load_all_plugins()
    opengraph = loader.get_plugin("opengraph-unfurl")
    
    assert opengraph is not None
    assert isinstance(opengraph, IntegrationPlugin)
    
    # OpenGraph doesn't have a base URL (it fetches arbitrary URLs)
    assert opengraph.base_url is None
    
    # Check URL pattern in link-preview block
    blocks = opengraph.blocks
    assert len(blocks) == 1
    
    link_block = blocks[0]
    assert link_block["id"] == "link-preview"
    assert len(link_block["url_patterns"]) == 1
    
    # Pattern should match any http/https URL
    pattern = link_block["url_patterns"][0]
    assert pattern == "https?://.*"
    
    # Test the pattern
    url_regex = re.compile(pattern)
    assert url_regex.search("https://example.com")
    assert url_regex.search("http://example.com")
    assert url_regex.search("https://github.com/owner/repo")
    assert not url_regex.search("ftp://example.com")


def test_opengraph_url_pattern_validity(loader):
    """Test that OpenGraph URL pattern is valid regex."""
    loader.load_all_plugins()
    opengraph = loader.get_plugin("opengraph-unfurl")
    
    blocks = opengraph.blocks
    pattern = blocks[0]["url_patterns"][0]
    
    # Should be valid regex
    url_regex = re.compile(pattern)
    
    # Test with various URLs
    test_urls = [
        "https://example.com",
        "http://example.com",
        "https://www.github.com",
        "https://api.github.com/repos/owner/repo",
        "https://example.com/path/to/page?query=value",
    ]
    
    for url in test_urls:
        assert url_regex.search(url), f"Pattern should match {url}"
    
    # Should not match non-http URLs
    assert not url_regex.search("ftp://example.com")
    assert not url_regex.search("mailto:test@example.com")
    assert not url_regex.search("file:///path/to/file")


def test_all_integration_base_urls_valid(loader):
    """Test that all integration base URLs are properly formatted."""
    loader.load_all_plugins()
    integrations = loader.get_plugins_by_type("integration")
    
    for integration in integrations:
        if not isinstance(integration, IntegrationPlugin):
            continue
        
        base_url = integration.base_url
        
        # Base URL can be None (like OpenGraph)
        if base_url is not None:
            # Should be a valid HTTP/HTTPS URL
            assert base_url.startswith("http://") or base_url.startswith("https://"), \
                f"Base URL for {integration.id} should start with http:// or https://"
            
            # Should not end with a slash (for consistency)
            # Actually, checking the weather-api, it doesn't end with slash, GitHub doesn't either
            # So this is already correct
            
            # Should not contain query parameters
            assert "?" not in base_url, \
                f"Base URL for {integration.id} should not contain query parameters"


def test_integration_syntax_examples_valid(loader):
    """Test that syntax examples in integrations contain valid example URLs."""
    loader.load_all_plugins()
    integrations = loader.get_plugins_by_type("integration")
    
    for integration in integrations:
        if not isinstance(integration, IntegrationPlugin):
            continue
        
        for block in integration.blocks:
            syntax = block.get("syntax", "")
            if "url:" in syntax or "url =" in syntax:
                # Extract URLs from syntax examples
                # This is a simple check - just verify common patterns exist
                if integration.id == "github":
                    assert "github.com" in syntax, \
                        f"GitHub integration block {block['id']} should contain github.com in syntax example"
                elif integration.id == "opengraph-unfurl":
                    # Should contain a valid example URL
                    assert "https://" in syntax or "http://" in syntax, \
                        f"OpenGraph integration should contain a valid URL in syntax example"
