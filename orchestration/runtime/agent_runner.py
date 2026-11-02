# Run agents with timeouts, tool permissions and readable execution logs.
import asyncio
import logging

from core import AgentResult, IncidentContext
from runtime import ToolExecutor, current_agent, current_incident

logger = logging.getLogger(__name__)


class AgentRunner:
    # Initialize AgentRunner with its dependencies and configuration.
    def __init__(self, tool_executor: ToolExecutor | None = None, timeout_seconds: int = 120):
        self.tools = tool_executor or ToolExecutor()
        self.timeout_seconds = timeout_seconds

    # Run an agent under its tool identity and timeout, then validate its result type.
    async def run(self, agent, context: IncidentContext | dict) -> AgentResult:
        if isinstance(context, dict):
            context = IncidentContext.from_state(context)

        from tools.permissions import agent_scope

        with agent_scope(type(agent).__name__):
            result = await asyncio.wait_for(agent.execute(context), getattr(agent, "timeout_seconds", self.timeout_seconds))
        if not isinstance(result, AgentResult):
            raise TypeError("Agent.execute() must return AgentResult")
        return result

    # Log a tool call and delegate permission checks and execution to ToolExecutor.
    async def execute_tool(
        self, name: str, arguments: dict | None = None, *, server: str | None = None
    ):
        number, agent = current_incident.get() or "-", current_agent.get()
        logger.info("[%s] %s: calling tool %s", number, agent, name)
        try:
            result = await self.tools.execute(name, arguments, server=server)
        except Exception as error:
            logger.warning("[%s] %s: tool %s failed (%s)", number, agent, name, type(error).__name__)
            raise
        logger.info("[%s] %s: tool %s completed", number, agent, name)
        return result

    # Return permitted tool metadata for the requested model-facing scope.
    def describe_tools(self, scope: str) -> dict:
        return self.tools.describe(scope)

    # Filter native function schemas using the executor's current-agent permissions.
    def filter_tool_schemas(self, schemas: list) -> list:
        return self.tools.filter_schemas(schemas)
