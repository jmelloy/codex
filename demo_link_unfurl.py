#!/usr/bin/env python3
"""Demo script for link unfurl functionality.

This script demonstrates:
1. How standalone URLs in markdown are detected
2. How they're converted to link-preview blocks
3. How the Open Graph scraper works
"""

import asyncio
from pathlib import Path

from codex.plugins.executor import IntegrationExecutor
from codex.plugins.loader import PluginLoader
from codex.plugins.opengraph_scraper import OpenGraphScraper


def demo_url_detection():
    """Demonstrate URL detection in markdown."""
    print("=" * 80)
    print("DEMO 1: URL Detection in Markdown")
    print("=" * 80)

    markdown_examples = [
        "9:00 - https://amazon.com",
        "Check this out: https://github.com",
        "https://www.reddit.com is interesting",
        "[This is a link](https://example.com) - not detected",
        "```python\nhttps://example.com\n``` - not detected in code blocks",
    ]

    print("\nOriginal Markdown:")
    for example in markdown_examples:
        print(f"  {example}")

    print("\nAfter URL Detection (conceptual):")
    for example in markdown_examples:
        if "https://" in example and "[" not in example and "```" not in example:
            url = example.split("https://")[1].split()[0]
            print(f"  {example} → Converted to link-preview block for https://{url}")
        else:
            print(f"  {example} → No conversion (in link or code block)")


def demo_opengraph_scraping():
    """Demonstrate Open Graph metadata scraping."""
    print("\n" + "=" * 80)
    print("DEMO 2: Open Graph Metadata Scraping")
    print("=" * 80)

    scraper = OpenGraphScraper()

    # Example HTML with Open Graph tags
    html = """
    <html>
    <head>
        <title>Example Page - Fallback Title</title>
        <meta property="og:title" content="Amazing Product - Buy Now!">
        <meta property="og:description" content="This is an amazing product that you should definitely check out. Limited time offer!">
        <meta property="og:image" content="https://example.com/images/product.jpg">
        <meta property="og:url" content="https://example.com/products/amazing">
        <meta property="og:site_name" content="Example Store">
    </head>
    <body>
        <h1>Product Page</h1>
    </body>
    </html>
    """

    print("\nInput HTML (excerpt):")
    print("  <meta property=\"og:title\" content=\"Amazing Product - Buy Now!\">")
    print("  <meta property=\"og:description\" content=\"This is an amazing product...\">")
    print("  <meta property=\"og:image\" content=\"https://example.com/images/product.jpg\">")

    print("\nParsed Metadata:")
    metadata = scraper._parse_og_tags(html)
    for key, value in metadata.items():
        print(f"  {key}: {value}")


async def demo_executor_integration():
    """Demonstrate integration executor with opengraph."""
    print("\n" + "=" * 80)
    print("DEMO 3: Integration Executor with OpenGraph Plugin")
    print("=" * 80)

    # Load plugins
    plugins_dir = Path(__file__).parent.parent / "plugins"
    loader = PluginLoader(plugins_dir)
    plugins = loader.load_all_plugins()

    print(f"\nLoaded {len(plugins)} plugins from {plugins_dir}")
    print(f"OpenGraph plugin found: {'opengraph-unfurl' in plugins}")

    if "opengraph-unfurl" in plugins:
        opengraph = plugins["opengraph-unfurl"]
        print(f"\nPlugin Details:")
        print(f"  ID: {opengraph.id}")
        print(f"  Name: {opengraph.name}")
        print(f"  Type: {opengraph.type}")
        print(f"  Auth Method: {opengraph.auth_method}")

        print(f"\nEndpoints:")
        for endpoint in opengraph.endpoints:
            print(f"  - {endpoint.get('id')}: {endpoint.get('name')}")

        print(f"\nBlocks:")
        for block in opengraph.blocks:
            print(f"  - {block.get('id')}: {block.get('name')}")


def demo_link_preview_component():
    """Show the LinkPreviewBlock component structure."""
    print("\n" + "=" * 80)
    print("DEMO 4: LinkPreviewBlock Component Flow")
    print("=" * 80)

    print("\n1. User Input:")
    print("   9:00 - https://amazon.com")

    print("\n2. URL Detection (Frontend - MarkdownViewer.vue):")
    print("   → Detects standalone URL")
    print("   → Converts to: ```link-preview\\nurl: https://amazon.com\\n```")

    print("\n3. Custom Block Parsing:")
    print("   → Parses block type: 'link-preview'")
    print("   → Extracts config: {url: 'https://amazon.com'}")
    print("   → Creates placeholder div with unique ID")

    print("\n4. Component Mounting:")
    print("   → LinkPreviewBlock.vue mounts in placeholder")
    print("   → Component props: {config: {url: '...'}, workspaceId, notebookId}")

    print("\n5. API Call:")
    print("   → POST /api/v1/workspaces/{id}/notebooks/{id}/integrations/opengraph-unfurl/execute")
    print("   → Body: {endpoint_id: 'fetch_metadata', parameters: {url: '...'}}")

    print("\n6. Backend Processing:")
    print("   → Executor detects opengraph-unfurl plugin")
    print("   → Calls OpenGraphScraper.scrape_url()")
    print("   → Fetches page HTML")
    print("   → Parses Open Graph tags")
    print("   → Returns metadata JSON")

    print("\n7. Frontend Rendering:")
    print("   → Component receives metadata")
    print("   → Renders rich preview card:")
    print("     - Preview image (if available)")
    print("     - Site name")
    print("     - Title")
    print("     - Description")
    print("     - Source URL")


def main():
    """Run all demos."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "LINK UNFURL DEMONSTRATION" + " " * 33 + "║")
    print("╚" + "=" * 78 + "╝")

    demo_url_detection()
    demo_opengraph_scraping()
    asyncio.run(demo_executor_integration())
    demo_link_preview_component()

    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\nTo test manually:")
    print("1. Start backend: cd backend && python -m codex.main")
    print("2. Start frontend: cd frontend && npm run dev")
    print("3. Create a notebook and add markdown with URLs")
    print("4. See link previews appear automatically!")
    print()


if __name__ == "__main__":
    main()
