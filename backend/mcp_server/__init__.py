"""
MCP Server for Codex Lab Notebook System

This module provides a Model Context Protocol (MCP) server that exposes
Codex functionality to AI assistants and other MCP clients.
"""

from .server import serve

__all__ = ["serve"]
