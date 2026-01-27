#!/usr/bin/env python3
"""
Screenshot utility for Codex.

Takes screenshots of different themes and pages for documentation and testing.
Requires the test data to be seeded first.

Usage:
    python -m codex.scripts.take_screenshots
    python -m codex.scripts.take_screenshots --themes-only
    python -m codex.scripts.take_screenshots --output-dir ./screenshots
"""

import argparse
import asyncio
from pathlib import Path

from playwright.async_api import Browser, Page, async_playwright

# Available themes in Codex
THEMES = [
    {"name": "cream", "label": "Cream"},
    {"name": "manila", "label": "Manila"},
    {"name": "white", "label": "White"},
    {"name": "blueprint", "label": "Blueprint"},
]

# Test user for screenshots
TEST_USER = {
    "username": "demo",
    "password": "demo123456",
}

# Pages to screenshot
PAGES = [
    {"path": "/login", "name": "login", "auth_required": False, "wait_for": "button[type='submit']"},
    {"path": "/register", "name": "register", "auth_required": False, "wait_for": "button[type='submit']"},
    {"path": "/", "name": "home", "auth_required": True, "wait_for": ".workspace-list, .notebook-list, h1"},
    {"path": "/settings", "name": "settings", "auth_required": True, "wait_for": "h1, .settings-content"},
]


async def login(page: Page, username: str, password: str):
    """Log in to the application."""
    print(f"🔐 Logging in as {username}...")
    await page.goto("http://localhost:5173/login")
    await page.wait_for_load_state("networkidle")

    # Fill in credentials
    await page.fill('input[type="text"]', username)
    await page.fill('input[type="password"]', password)

    # Click login
    await page.click('button[type="submit"]')
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(2)  # Wait for redirect


async def set_theme(page: Page, theme_name: str, theme_slug: str):
    """Set the theme by directly manipulating the DOM."""
    try:
        # Create the CSS class name (e.g., "cream" -> "theme-cream")
        theme_class = f"theme-{theme_slug}"

        # Remove all theme classes from body
        await page.evaluate("""
            () => {
                document.body.classList.remove('theme-cream', 'theme-manila', 'theme-white', 'theme-blueprint');
            }
        """)

        # Add the new theme class to body
        await page.evaluate(f"""
            () => {{
                document.body.classList.add('{theme_class}');
            }}
        """)

        # Also update the main app div if it exists
        await page.evaluate(f"""
            () => {{
                const appDiv = document.querySelector('.w-full.h-screen');
                if (appDiv) {{
                    appDiv.classList.remove('theme-cream', 'theme-manila', 'theme-white', 'theme-blueprint');
                    appDiv.classList.add('{theme_class}');
                }}
            }}
        """)

        await asyncio.sleep(0.5)  # Wait for CSS to apply
        print(f"  ✓ Set theme to {theme_name} (class: {theme_class})")
    except Exception as e:
        print(f"  ⚠️  Could not set theme: {e}")


async def take_page_screenshot(
    page: Page, url: str, filename: str, wait_for: str = None, viewport: dict[str, int] = None
):
    """Take a screenshot of a specific page."""
    if viewport:
        await page.set_viewport_size(viewport)

    await page.goto(url)
    await page.wait_for_load_state("networkidle")

    if wait_for:
        try:
            await page.wait_for_selector(wait_for, timeout=5000)
        except Exception as e:
            print(f"  ⚠️  Wait selector '{wait_for}' not found: {e}")

    await asyncio.sleep(1)
    await page.screenshot(path=filename, full_page=False)
    print(f"  ✓ Saved: {filename}")


async def take_theme_screenshots(browser: Browser, output_dir: Path):
    """Take screenshots of all themes on the home page."""
    print("\n📸 Taking theme screenshots...")

    page = await browser.new_page(viewport={"width": 1920, "height": 1080})

    try:
        # Login first
        await login(page, TEST_USER["username"], TEST_USER["password"])

        # Navigate to home page
        await page.goto("http://localhost:5173/")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

        # Take screenshot for each theme
        for theme in THEMES:
            print(f"\n  Theme: {theme['label']}")

            # Set the theme
            await set_theme(page, theme["label"], theme["name"])

            # Take screenshot
            filename = output_dir / f"theme-{theme['name']}.png"
            await page.screenshot(path=str(filename))
            print(f"  ✓ Saved: {filename}")

            await asyncio.sleep(1)

    finally:
        await page.close()


async def take_page_screenshots(browser: Browser, output_dir: Path):
    """Take screenshots of all pages."""
    print("\n📸 Taking page screenshots...")

    page = await browser.new_page(viewport={"width": 1920, "height": 1080})
    authenticated = False

    try:
        for page_info in PAGES:
            page_name = page_info["name"]
            page_path = page_info["path"]
            auth_required = page_info["auth_required"]
            wait_for = page_info.get("wait_for")

            print(f"\n  Page: {page_name} ({page_path})")

            # Login if needed
            if auth_required and not authenticated:
                await login(page, TEST_USER["username"], TEST_USER["password"])
                authenticated = True

            # Take screenshot
            url = f"http://localhost:5173{page_path}"
            filename = output_dir / f"page-{page_name}.png"
            await take_page_screenshot(page, url, str(filename), wait_for)

    finally:
        await page.close()


async def take_workflow_screenshots(browser: Browser, output_dir: Path):
    """Take screenshots of common workflows."""
    print("\n📸 Taking workflow screenshots...")

    page = await browser.new_page(viewport={"width": 1920, "height": 1080})

    try:
        # Workflow 1: Login flow
        print("\n  Workflow: Login")
        await page.goto("http://localhost:5173/login")
        await page.wait_for_load_state("networkidle")

        # Empty login page
        filename = output_dir / "workflow-login-empty.png"
        await page.screenshot(path=str(filename))
        print(f"  ✓ Saved: {filename}")

        # Filled login page
        await page.fill('input[type="text"]', TEST_USER["username"])
        await page.fill('input[type="password"]', TEST_USER["password"])
        filename = output_dir / "workflow-login-filled.png"
        await page.screenshot(path=str(filename))
        print(f"  ✓ Saved: {filename}")

        # After login - home page
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        filename = output_dir / "workflow-home-after-login.png"
        await page.screenshot(path=str(filename))
        print(f"  ✓ Saved: {filename}")

        # Workflow 2: Navigate to workspace/notebook
        print("\n  Workflow: Browse notebooks")

        # Try to click on a workspace
        try:
            workspace_link = page.locator("text=Machine Learning Lab, .workspace-item, [data-workspace-name]").first
            if await workspace_link.count() > 0:
                await workspace_link.click()
                await asyncio.sleep(2)
                filename = output_dir / "workflow-workspace-selected.png"
                await page.screenshot(path=str(filename))
                print(f"  ✓ Saved: {filename}")

                # Try to click on a notebook
                notebook_link = page.locator("text=Neural Networks, .notebook-item, [data-notebook-name]").first
                if await notebook_link.count() > 0:
                    await notebook_link.click()
                    await asyncio.sleep(2)
                    filename = output_dir / "workflow-notebook-selected.png"
                    await page.screenshot(path=str(filename))
                    print(f"  ✓ Saved: {filename}")
        except Exception as e:
            print(f"  ⚠️  Could not complete workflow: {e}")

    finally:
        await page.close()


async def take_mobile_screenshots(browser: Browser, output_dir: Path):
    """Take screenshots with mobile viewport."""
    print("\n📱 Taking mobile screenshots...")

    mobile_viewport = {"width": 375, "height": 667}  # iPhone SE size
    page = await browser.new_page(viewport=mobile_viewport)

    try:
        # Login page
        print("\n  Mobile: Login")
        url = "http://localhost:5173/login"
        filename = output_dir / "mobile-login.png"
        await take_page_screenshot(page, url, str(filename))

        # Login and take home page
        await login(page, TEST_USER["username"], TEST_USER["password"])

        print("\n  Mobile: Home")
        filename = output_dir / "mobile-home.png"
        await page.screenshot(path=str(filename))
        print(f"  ✓ Saved: {filename}")

    finally:
        await page.close()


async def main(args):
    """Main screenshot function."""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"📁 Output directory: {output_dir}")
    print("🌐 Target URL: http://localhost:5173")
    print(f"👤 Test user: {TEST_USER['username']}")

    async with async_playwright() as p:
        browser = await p.chromium.launch()

        try:
            if args.themes_only:
                await take_theme_screenshots(browser, output_dir)
            elif args.pages_only:
                await take_page_screenshots(browser, output_dir)
            elif args.workflows_only:
                await take_workflow_screenshots(browser, output_dir)
            elif args.mobile_only:
                await take_mobile_screenshots(browser, output_dir)
            else:
                # Take all screenshots
                await take_page_screenshots(browser, output_dir)
                await take_theme_screenshots(browser, output_dir)
                await take_workflow_screenshots(browser, output_dir)
                await take_mobile_screenshots(browser, output_dir)

            print("\n✅ Screenshot capture complete!")
            print(f"📁 Screenshots saved to: {output_dir.absolute()}")

        finally:
            await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Take screenshots of Codex for documentation and testing")
    parser.add_argument(
        "--output-dir",
        default="./screenshots",
        help="Output directory for screenshots (default: ./screenshots)",
    )
    parser.add_argument(
        "--themes-only",
        action="store_true",
        help="Only take theme screenshots",
    )
    parser.add_argument(
        "--pages-only",
        action="store_true",
        help="Only take page screenshots",
    )
    parser.add_argument(
        "--workflows-only",
        action="store_true",
        help="Only take workflow screenshots",
    )
    parser.add_argument(
        "--mobile-only",
        action="store_true",
        help="Only take mobile screenshots",
    )

    args = parser.parse_args()
    asyncio.run(main(args))
