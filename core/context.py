# Carry incident state and temporary evidence between agents during one workflow run.
from dataclasses import dataclass, field
from contextvars import ContextVar
from typing import Any

run_evidence = ContextVar("run_evidence", default=None)


@dataclass
class IncidentContext:
    incident_id: str
    state: dict[str, Any]
    evidence: dict[str, Any] = field(default_factory=dict)

    # Build an incident context from checkpoint fields and the current in-memory evidence.
    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "IncidentContext":
        incident_id = state.get("sys_id") or state.get("incident_id")
        if not incident_id:
            raise ValueError("Incident state requires sys_id or incident_id")
        return cls(
            incident_id=incident_id,
            state=dict(state),
            evidence=run_evidence.get() if run_evidence.get() is not None else {},
        )
