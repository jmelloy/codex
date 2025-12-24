# Codex MCP Server

This directory contains the Model Context Protocol (MCP) server for Codex, enabling AI assistants like GitHub Copilot to interact with the Codex lab notebook system.

## Features

- **Server Management**: Start/stop frontend and backend development servers
- **Screenshot Capability**: Take screenshots of the frontend or any URL
- **Browser Automation**: Navigate to specific pages and wait for elements
- **Resource Cleanup**: Properly shutdown servers and browser instances

## Installation

1. Install Codex with MCP dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

2. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

## Configuration

The MCP server is configured in `.github/mcp-server.json`. To use it with an MCP client:

1. Point your MCP client to the configuration file
2. The server will be available under the name "codex"

### GitHub Copilot Configuration

For GitHub Copilot, add this to your settings:

```json
{
  "github.copilot.mcp": {
    "codex": {
      "command": "python",
      "args": ["-m", "backend.mcp_server"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

## Available Tools

### start_frontend
Start the Codex frontend development server on port 5173.

**Parameters**: None

**Returns**: Status message with server URL and PID

### start_backend
Start the Codex backend API server on port 8000.

**Parameters**: None

**Returns**: Status message with server URLs (API and docs) and PID

### take_screenshot
Take a screenshot of the frontend or any URL.

**Parameters**:
- `url` (string, optional): URL to screenshot (default: http://localhost:5173)
- `path` (string, optional): Path to save screenshot (default: screenshot.png)

**Returns**: Status message with screenshot path

### navigate_and_screenshot
Navigate to a URL, optionally wait for a CSS selector, and take a screenshot.

**Parameters**:
- `url` (string, required): URL to navigate to
- `selector` (string, optional): CSS selector to wait for before taking screenshot
- `path` (string, optional): Path to save screenshot (default: screenshot.png)

**Returns**: Status message with screenshot path and navigation details

### cleanup
Stop all servers and clean up browser resources.

**Parameters**: None

**Returns**: Status message with cleanup details

## Usage Examples

### Example 1: Start servers and take screenshot

```python
# Start the frontend server
result = await call_tool("start_frontend", {})
# Output: {"status": "started", "url": "http://localhost:5173", "pid": 12345}

# Wait a moment for the server to be fully ready
await asyncio.sleep(2)

# Take a screenshot of the home page
result = await call_tool("take_screenshot", {
    "url": "http://localhost:5173",
    "path": "homepage.png"
})
# Output: {"status": "success", "path": "/path/to/homepage.png"}
```

### Example 2: Navigate and screenshot a specific page

```python
# Start both servers
await call_tool("start_backend", {})
await call_tool("start_frontend", {})

# Navigate to notebooks page and wait for the list to load
result = await call_tool("navigate_and_screenshot", {
    "url": "http://localhost:5173/notebooks",
    "selector": ".notebook-list",
    "path": "notebooks-page.png"
})
# Output: {"status": "success", "path": "/path/to/notebooks-page.png"}
```

### Example 3: Clean up resources

```python
# When done, clean up all resources
result = await call_tool("cleanup", {})
# Output: {"status": "success", "details": ["Browser closed", "Frontend server stopped", ...]}
```

## Development

To run the MCP server manually for testing:

```bash
python -m backend.mcp_server
```

The server communicates via stdio (standard input/output) using the MCP protocol.

## Architecture

The MCP server (`server.py`) implements:

1. **Process Management**: Manages subprocess lifecycle for frontend/backend servers
2. **Browser Automation**: Uses Playwright for browser control and screenshots
3. **MCP Protocol**: Implements the Model Context Protocol for tool exposure
4. **Resource Cleanup**: Ensures proper shutdown of all managed resources

## Troubleshooting

### Server won't start
- Check that ports 5173 (frontend) and 8000 (backend) are available
- Ensure dependencies are installed: `pip install -e ".[dev]"`
- Check that npm is available for frontend: `npm --version`

### Screenshots fail
- Ensure Playwright browsers are installed: `playwright install chromium`
- Check that the server is running and accessible
- Verify the URL is correct

### Browser initialization errors
- Install Playwright browsers: `playwright install chromium`
- On Linux, you may need additional dependencies: `playwright install-deps chromium`

## Security Considerations

- The MCP server should only be run in trusted development environments
- Server processes are started locally and not exposed beyond localhost
- Screenshots are saved to the project directory by default
- Always call `cleanup` to properly shutdown resources

## License

MIT License - see LICENSE file for details
