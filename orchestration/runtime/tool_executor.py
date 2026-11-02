# Enforce agent permissions and execute registered local or MCP tools.
import asyncio
import inspect
from copy import deepcopy
from .mcp_gateway import call_mcp
from .logging_setup import current_agent


class ToolExecutor:
    # Initialize ToolExecutor with its dependencies and configuration.
    def __init__(self):
        self.local_tools = {}
        self.mcp_sessions = {}
        self.remote_tools = {}
        self.descriptions = {}

    # Register a local tool callable and copy its optional metadata.
    def register_local(self, name: str, tool, *, description=None):
        self.local_tools[name] = tool
        if description is not None:
            self.descriptions[name] = deepcopy(description)

    # Return tool descriptions matching the requested scope and agent permissions.
    def describe(self, scope: str, *, agent: str | None = None) -> dict:
        from tools.permissions import allowed_tools

        allowed = allowed_tools(agent or current_agent.get())
        return deepcopy({name: spec for name, spec in self.descriptions.items()
                         if name in allowed and spec.get("scope") == scope})

    # Hide native LLM function schemas that the current agent is not permitted to execute.
    def filter_schemas(self, schemas: list) -> list:
        from tools.permissions import allowed_tools

        allowed = allowed_tools(current_agent.get())
        return [schema for schema in schemas if schema['function']['name'] in allowed]

    # Attach an initialized MCP session under its server name.
    def register_mcp(self, server: str, session):
        self.mcp_sessions[server] = session

    # Bind a registered tool to an MCP server and remove any local fallback.
    def register_remote(self, name: str, server: str):
        if server not in self.mcp_sessions:
            raise ValueError("MCP session is not connected")
        self.remote_tools[name] = server
        self.local_tools.pop(name, None)

    # Reject unauthorized or misrouted calls, then execute the local or MCP tool.
    async def execute(
        self, name: str, arguments: dict | None = None, *, server: str | None = None
    ):
        from tools.permissions import allowed_tools

        agent = current_agent.get()
        if name not in allowed_tools(agent):
            raise PermissionError(f'{agent} may not execute tool {name}')
        if server is not None and server != self.remote_tools.get(name):
            raise PermissionError('Tool server does not match its registered route')
        arguments = arguments or {}
        server = server or self.remote_tools.get(name)
        if server is not None:
            return await call_mcp(self.mcp_sessions[server], name, arguments)

        tool = self.local_tools[name]
        if inspect.iscoroutinefunction(tool):
            return await tool(**arguments)
        result = await asyncio.to_thread(tool, **arguments)
        return await result if inspect.isawaitable(result) else result
