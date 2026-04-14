"""
Google Maps MCP Integration
----------------------------
This module creates a connection to the Google Maps MCP server
(@modelcontextprotocol/server-google-maps) using the OpenAI Agents SDK.

The MCP server exposes tools like:
  - maps_geocode          → convert address to lat/lng
  - maps_directions       → get route, distance, duration
  - maps_search_nearby    → find places near a location
  - maps_place_details    → details on a specific place

Agents that receive this MCP server can call any of those tools
just like they would call a regular function_tool.

SETUP: Run `npm install -g @modelcontextprotocol/server-google-maps`
before starting the backend, or rely on npx (handled automatically below).
"""

import os
from agents.mcp import MCPServerStdio
from config import GOOGLE_API_KEY


def get_google_maps_mcp() -> MCPServerStdio:
    """
    Returns an MCPServerStdio instance connected to the Google Maps MCP server.

    Usage:
        async with get_google_maps_mcp() as mcp:
            agent = Agent(..., mcp_servers=[mcp])
            result = await Runner.run(agent, input="...")
    """
    return MCPServerStdio(
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-google-maps"],
            "env": {
                **os.environ,
                "GOOGLE_MAPS_API_KEY": GOOGLE_API_KEY,
            },
        },
        # Cache the tool list so we don't re-fetch on every agent run
        cache_tools_list=True,
    )
