"""
MCP Server implementation for Codex.

Provides tools for:
- Starting/stopping the frontend dev server
- Taking screenshots of the frontend
- Interacting with the Codex API
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from playwright.async_api import async_playwright, Browser, Page


# Global state for managing processes and browser
_frontend_process: subprocess.Popen | None = None
_backend_process: subprocess.Popen | None = None
_browser: Browser | None = None
_page: Page | None = None


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


async def start_frontend() -> dict[str, Any]:
    """Start the frontend development server."""
    global _frontend_process
    
    if _frontend_process and _frontend_process.poll() is None:
        return {
            "status": "already_running",
            "message": "Frontend server is already running",
            "url": "http://localhost:5173"
        }
    
    frontend_dir = get_project_root() / "frontend"
    
    try:
        # Start the frontend dev server
        _frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for the server to start
        await asyncio.sleep(3)
        
        return {
            "status": "started",
            "message": "Frontend server started successfully",
            "url": "http://localhost:5173",
            "pid": _frontend_process.pid
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to start frontend server: {str(e)}"
        }


async def start_backend() -> dict[str, Any]:
    """Start the backend API server."""
    global _backend_process
    
    if _backend_process and _backend_process.poll() is None:
        return {
            "status": "already_running",
            "message": "Backend server is already running",
            "url": "http://localhost:8000"
        }
    
    project_root = get_project_root()
    
    try:
        # Start the backend server
        _backend_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.api.main:app", "--reload", "--port", "8000"],
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for the server to start
        await asyncio.sleep(3)
        
        return {
            "status": "started",
            "message": "Backend server started successfully",
            "url": "http://localhost:8000",
            "api_docs": "http://localhost:8000/docs",
            "pid": _backend_process.pid
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to start backend server: {str(e)}"
        }


async def initialize_browser() -> dict[str, Any]:
    """Initialize the Playwright browser."""
    global _browser, _page
    
    if _browser and _page:
        return {
            "status": "already_initialized",
            "message": "Browser is already initialized"
        }
    
    try:
        playwright = await async_playwright().start()
        _browser = await playwright.chromium.launch(headless=True)
        _page = await _browser.new_page()
        
        return {
            "status": "initialized",
            "message": "Browser initialized successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to initialize browser: {str(e)}"
        }


async def take_screenshot(url: str = "http://localhost:5173", path: str = "screenshot.png") -> dict[str, Any]:
    """
    Take a screenshot of the frontend.
    
    Args:
        url: The URL to screenshot (default: frontend dev server)
        path: Path to save the screenshot (default: screenshot.png)
    """
    global _browser, _page
    
    # Initialize browser if needed
    if not _browser or not _page:
        init_result = await initialize_browser()
        if init_result["status"] == "error":
            return init_result
    
    try:
        # Navigate to the URL
        await _page.goto(url, wait_until="networkidle")
        
        # Take screenshot
        screenshot_path = get_project_root() / path
        await _page.screenshot(path=str(screenshot_path), full_page=True)
        
        return {
            "status": "success",
            "message": f"Screenshot saved successfully",
            "path": str(screenshot_path),
            "url": url
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to take screenshot: {str(e)}"
        }


async def navigate_and_screenshot(url: str, selector: str | None = None, path: str = "screenshot.png") -> dict[str, Any]:
    """
    Navigate to a URL and take a screenshot, optionally waiting for a selector.
    
    Args:
        url: The URL to navigate to
        selector: Optional CSS selector to wait for before taking screenshot
        path: Path to save the screenshot
    """
    global _browser, _page
    
    # Initialize browser if needed
    if not _browser or not _page:
        init_result = await initialize_browser()
        if init_result["status"] == "error":
            return init_result
    
    try:
        # Navigate to the URL
        await _page.goto(url, wait_until="networkidle")
        
        # Wait for selector if provided
        if selector:
            await _page.wait_for_selector(selector, timeout=10000)
        
        # Take screenshot
        screenshot_path = get_project_root() / path
        await _page.screenshot(path=str(screenshot_path), full_page=True)
        
        return {
            "status": "success",
            "message": f"Screenshot saved successfully",
            "path": str(screenshot_path),
            "url": url,
            "selector": selector
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to navigate and screenshot: {str(e)}"
        }


async def cleanup() -> dict[str, Any]:
    """Clean up processes and browser."""
    global _frontend_process, _backend_process, _browser, _page
    
    messages = []
    
    # Close browser
    if _browser:
        try:
            await _browser.close()
            _browser = None
            _page = None
            messages.append("Browser closed")
        except Exception as e:
            messages.append(f"Error closing browser: {str(e)}")
    
    # Stop frontend
    if _frontend_process and _frontend_process.poll() is None:
        try:
            _frontend_process.terminate()
            _frontend_process.wait(timeout=5)
            _frontend_process = None
            messages.append("Frontend server stopped")
        except Exception as e:
            messages.append(f"Error stopping frontend: {str(e)}")
    
    # Stop backend
    if _backend_process and _backend_process.poll() is None:
        try:
            _backend_process.terminate()
            _backend_process.wait(timeout=5)
            _backend_process = None
            messages.append("Backend server stopped")
        except Exception as e:
            messages.append(f"Error stopping backend: {str(e)}")
    
    return {
        "status": "success",
        "message": "Cleanup completed",
        "details": messages
    }


# Create the MCP server
app = Server("codex")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="start_frontend",
            description="Start the Codex frontend development server on port 5173",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="start_backend",
            description="Start the Codex backend API server on port 8000",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="take_screenshot",
            description="Take a screenshot of the frontend or any URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to screenshot (default: http://localhost:5173)",
                        "default": "http://localhost:5173"
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to save screenshot (default: screenshot.png)",
                        "default": "screenshot.png"
                    }
                },
            },
        ),
        Tool(
            name="navigate_and_screenshot",
            description="Navigate to a URL, optionally wait for a CSS selector, and take a screenshot",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to navigate to",
                    },
                    "selector": {
                        "type": "string",
                        "description": "Optional CSS selector to wait for before taking screenshot",
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to save screenshot (default: screenshot.png)",
                        "default": "screenshot.png"
                    }
                },
                "required": ["url"]
            },
        ),
        Tool(
            name="cleanup",
            description="Stop all servers and clean up resources",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "start_frontend":
            result = await start_frontend()
        elif name == "start_backend":
            result = await start_backend()
        elif name == "take_screenshot":
            result = await take_screenshot(
                url=arguments.get("url", "http://localhost:5173"),
                path=arguments.get("path", "screenshot.png")
            )
        elif name == "navigate_and_screenshot":
            result = await navigate_and_screenshot(
                url=arguments["url"],
                selector=arguments.get("selector"),
                path=arguments.get("path", "screenshot.png")
            )
        elif name == "cleanup":
            result = await cleanup()
        else:
            result = {
                "status": "error",
                "message": f"Unknown tool: {name}"
            }
        
        return [TextContent(type="text", text=str(result))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


def serve():
    """Start the MCP server."""
    asyncio.run(stdio_server(app))


if __name__ == "__main__":
    serve()
