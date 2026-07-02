"""Weather Agent connected to a Streamable HTTP MCP server."""
import os
import logging

from google.adk import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

logger.info(f"🌐 Initializing weather agent with remote MCP server")
logger.info(f"📡 MCP Server: {MCP_SERVER_URL}")

connection_params = StreamableHTTPConnectionParams(url=MCP_SERVER_URL, timeout=30.0)
weather_tools = McpToolset(connection_params=connection_params)

root_agent = Agent(
    name="weather_agent",
    model=MODEL,
    description="Weather assistant backed by live tools from a remote MCP server.",
    instruction=(
        "Use the MCP weather tools for weather questions. Never invent weather data. "
        "Use health_check when diagnosing server connectivity."
    ),
    tools=[weather_tools],
)
logger.info("Weather agent initialized with model %s and MCP server %s", MODEL, MCP_SERVER_URL)

