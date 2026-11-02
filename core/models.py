# Define agent results and convert them into checkpoint state updates.
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    # Convert this agent result into graph state fields and a stage event.
    def to_state_update(self, stage: str) -> dict[str, Any]:
        return {
            **self.output,
            "current_stage": stage,
            "workflow_status": self.status,
            "error": self.error,
            "events": [{"stage": stage, "status": self.status, "error": self.error}],
        }
