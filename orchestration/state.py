# Define the checkpointed state fields shared by the LangGraph workflow.
from operator import add
from typing import Annotated, Any, NotRequired, TypedDict


class IncidentState(TypedDict):
    sys_id: str
    incident_number: str
    events: Annotated[list[dict[str, Any]], add]

    category: NotRequired[str | None]
    classification_complete: NotRequired[bool]
    retriage_requested: NotRequired[bool]
    rediagnose_requested: NotRequired[bool]
    last_triage_fingerprint: NotRequired[str]
    user_requests: NotRequired[list[str]]
    active_user_request: NotRequired[str | None]
    user_request_details: NotRequired[dict[str, Any] | None]
    user_request_at: NotRequired[str | None]
    request_analysis: NotRequired[dict[str, Any] | None]
    clear_user_request: NotRequired[bool]
    request_to_user: NotRequired[str]
    skip_update: NotRequired[bool]
    processing_update: NotRequired[bool]
    triage: NotRequired[dict[str, Any]]
    caller_identity: NotRequired[dict[str, Any]]
    diagnosis: NotRequired[dict[str, Any]]
    previous_diagnosis: NotRequired[dict[str, Any]]
    resolution: NotRequired[dict[str, Any]]
    verification: NotRequired[dict[str, Any]]
    communication: NotRequired[dict[str, Any]]
    post_incident: NotRequired[dict[str, Any]]
    knowledge_graph_issue: NotRequired[dict[str, Any] | None]
    knowledge_graph_status: NotRequired[str]
    screenshot_ocr: NotRequired[dict[str, Any]]
    screenshot_present: NotRequired[bool | None]
    next_action: NotRequired[str | None]
    current_stage: NotRequired[str]
    workflow_status: NotRequired[str]
    error: NotRequired[str | None]
