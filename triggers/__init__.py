# Active ServiceNow webhook entry point.
"""Active ServiceNow webhook entry point."""
from .servicenow_webhook import IncidentPayload, router as servicenow_router

__all__ = ["IncidentPayload", "servicenow_router"]
