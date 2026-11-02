# Own MCP server lifetimes and normalize remote tool responses.
"""Own MCP server lifetimes and normalize remote tool responses."""
from contextlib import AsyncExitStack, asynccontextmanager
import json
import logging
from pathlib import Path
import sys

import httpx
from mcp import ClientSession, StdioServerParameters, stdio_client

from .logging_setup import current_incident

logger = logging.getLogger(__name__)


# Start the MCP servers, verify advertised tool coverage and close sessions on exit.
@asynccontextmanager
async def connect_mcp_servers():
    from tools.registry import gateway_tools
    root = Path(__file__).resolve().parents[1]
    async with AsyncExitStack() as stack:
        sessions = {}
        for name, required in gateway_tools().items():
            params = StdioServerParameters(command=sys.executable,
                args=["-u", "-m", f"mcp_servers.{name}.server"], cwd=root)
            streams = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(*streams, read_timeout_seconds=90))
            await session.initialize()
            advertised = {tool.name for tool in (await session.list_tools()).tools}
            if not set(required).issubset(advertised):
                raise RuntimeError(f"MCP server {name} is missing required tools")
            sessions[name] = session
            logger.info("MCP server connected: %s | Tools: %s", name, len(required))
        yield sessions


# Call an MCP tool with incident context and unwrap its result or sanitized failure.
async def call_mcp(session, name, arguments):
    response = await session.call_tool(name, arguments={
        **arguments, "incident_number": current_incident.get(),
    })
    if response.is_error:
        raise RuntimeError(f"MCP tool {name} failed")
    data = response.structured_content
    if data is None:
        texts = [item.text for item in response.content if item.type == "text"]
        if len(texts) != 1:
            raise ValueError("Invalid MCP tool response")
        data = json.loads(texts[0])
    if not isinstance(data, dict):
        raise ValueError("Invalid MCP response envelope")
    if data.get("error"):
        if data.get("error") == "HTTPStatusError":
            raise httpx.HTTPStatusError("MCP backend HTTP failure", request=httpx.Request("GET", "http://mcp-gateway"),
                                       response=httpx.Response(data["http_status"], json=data.get("body")))
        network_errors = {error.__name__: error for error in (
            httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError, httpx.ReadTimeout,
        )}
        if data["error"] in network_errors:
            raise network_errors[data["error"]]("MCP backend request failed")
        if data["error"] in ("ValueError", "TypeError", "KeyError"):
            raise ValueError("MCP gateway rejected tool arguments")
        raise RuntimeError(f"MCP tool {name} failed ({data['error']})")
    if "result" not in data:
        raise ValueError("Missing MCP tool result")
    return data["result"]
