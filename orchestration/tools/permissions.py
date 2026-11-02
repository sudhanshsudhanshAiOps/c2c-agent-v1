# Agent tool access policy, shared by execution and model tool visibility.
"""Agent tool access policy, shared by execution and model tool visibility."""
from contextlib import contextmanager
from types import MappingProxyType


AGENT_TOOLS = MappingProxyType({
    'TriageAgent': frozenset({
        'fetch_incident', 'fetch_caller_global_id', 'resolve_c2c_student',
        'fetch_students', 'read_incident_screenshots', 'fetch_caller_replies',
        'classify_incident', 'analyze_request',
    }),
    'DiagnosisAgent': frozenset({
        'diagnosis_scenarios', 'load_category_skill', 'next_diagnosis_action',
        'finish_diagnosis', 'load_scenario_skill', 'fetch_students', 'fetch_user_information',
        'fetch_user_todo_learning_items', 'fetch_learning_item_details',
        'fetch_items', 'fetch_catalog_items', 'fetch_curriculum_statuses',
        'fetch_curriculum_item_statuses', 'fetch_scheduled_offerings',
        'fetch_enrollment_listings', 'fetch_learning_history', 'fetch_curricula',
    }),
    'CommunicationAgent': frozenset({
        'list_screenshots', 'load_communication_skill',
        'compose_communication', 'update_incident',
    }),
})


# Return the permitted tool names for an agent, or an empty set for an unknown agent.
def allowed_tools(agent: str) -> frozenset:
    return AGENT_TOOLS.get(agent, frozenset())


# Establish agent identity for runner execution and standalone checks.
@contextmanager
def agent_scope(agent: str):
    """Establish agent identity for runner execution and standalone checks."""
    from runtime.logging_setup import current_agent

    if agent not in AGENT_TOOLS:
        raise PermissionError('Unknown tool agent: ' + agent)
    token = current_agent.set(agent)
    try:
        yield
    finally:
        current_agent.reset(token)
