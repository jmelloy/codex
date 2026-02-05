#!/usr/bin/env python3
"""Demo script for OpenGraph fallback to opengraph.io API.

This script demonstrates the fallback mechanism for OpenGraph scraping.
It shows how the scraper:
1. Attempts direct HTML scraping first
2. Falls back to opengraph.io API if direct scraping fails
3. Requires OPENGRAPH_IO_API_KEY environment variable for fallback

Usage:
    # Test with direct scraping (works for most sites)
    python demo_opengraph_fallback.py https://example.com

    # Test with a URL that might fail direct scraping
    # Set OPENGRAPH_IO_API_KEY environment variable first
    export OPENGRAPH_IO_API_KEY=your-api-key
    python demo_opengraph_fallback.py https://some-protected-site.com
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from codex.plugins.opengraph_scraper import OpenGraphScraper


async def demo_scraping(url: str):
    """Demonstrate OpenGraph scraping with fallback."""
    print("=" * 80)
    print("OpenGraph Fallback Demo")
    print("=" * 80)
    print()
    
    # Check if API key is set
    api_key = os.getenv("OPENGRAPH_IO_API_KEY")
    if api_key:
        print(f"✓ OPENGRAPH_IO_API_KEY is set (length: {len(api_key)})")
        print("  Fallback to opengraph.io API is available")
    else:
        print("✗ OPENGRAPH_IO_API_KEY is not set")
        print("  Only direct HTML scraping will be attempted")
    print()
    
    # Create scraper
    scraper = OpenGraphScraper(timeout=10)
    print(f"Scraping URL: {url}")
    print("-" * 80)
    print()
    
    try:
        # Attempt to scrape
        metadata = await scraper.scrape_url(url)
        
        # Display results
        print("✓ Successfully retrieved OpenGraph metadata:")
        print()
        
        if "title" in metadata:
            print(f"  Title:       {metadata['title']}")
        
        if "description" in metadata:
            desc = metadata['description']
            if len(desc) > 100:
                desc = desc[:97] + "..."
            print(f"  Description: {desc}")
        
        if "image" in metadata:
            print(f"  Image:       {metadata['image']}")
        
        if "url" in metadata:
            print(f"  URL:         {metadata['url']}")
        
        if "site_name" in metadata:
            print(f"  Site Name:   {metadata['site_name']}")
        
        print()
        print(f"Total fields: {len(metadata)}")
        
    except Exception as e:
        print(f"✗ Failed to scrape: {type(e).__name__}: {e}")
        if not api_key:
            print()
            print("Tip: Set OPENGRAPH_IO_API_KEY to enable fallback:")
            print("  export OPENGRAPH_IO_API_KEY=your-api-key")
    
    print()
    print("=" * 80)


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python demo_opengraph_fallback.py <url>")
        print()
        print("Examples:")
        print("  python demo_opengraph_fallback.py https://github.com")
        print("  python demo_opengraph_fallback.py https://python.org")
        sys.exit(1)
    
    url = sys.argv[1]
    await demo_scraping(url)


if __name__ == "__main__":
    asyncio.run(main())
