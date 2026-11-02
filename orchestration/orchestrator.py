# Run the incident graph with isolated in-memory evidence and scoped logging.
from core import run_evidence
from runtime import incident_scope


class Orchestrator:
    # Initialize Orchestrator with its dependencies and configuration.
    def __init__(self, graph):
        self.graph = graph

    # Invoke the checkpointed graph with isolated temporary evidence and incident logging.
    async def run(self, incident_id, initial_state):
        config = {
            "configurable": {
                "thread_id": incident_id
            }
        }

        token = run_evidence.set({})
        try:
            with incident_scope(initial_state["incident_number"]):
                return await self.graph.ainvoke(initial_state, config=config)
        finally:
            run_evidence.reset(token)
