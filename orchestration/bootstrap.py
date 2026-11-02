# Construct the agents, bind the tool registry and assemble the incident workflow.
import os

from agents import CommunicationAgent, DiagnosisAgent, TriageAgent
from mcp_servers import servicenow
from orchestration import IncidentState, Orchestrator, build_graph, create_agent_node
from runtime import AgentRunner, ToolExecutor
from tools.request_analyser import assess_user_reply, analyze_request
from functools import partial
from tools import (
    classify_incident, diagnosis_scenarios,
    read_incident_screenshots, register_tools, resolve_c2c_student,
)


# Bind tool implementations and agent model callbacks, then construct the shared incident graph.
def create_orchestrator(
    checkpointer=None,
    classifier=classify_incident,
    scenario_lookup=diagnosis_scenarios,
    diagnosis_reasoner=None,
    c2c_tools=None,
    screenshot_reader=read_incident_screenshots,
    incident_fetcher=servicenow.fetch_incident_by_sys_id,
    screenshot_lister=servicenow.list_screenshots,
    ticket_updater=servicenow.update_incident,
    communication_channels=("comments", "work_notes"),
    awaiting_state=None,
    in_progress_state=None,
    caller_global_id_fetcher=servicenow.fetch_caller_global_id,
    student_resolver=None,
    communication_reasoner=None,
    mcp_sessions=None,
    caller_reply_fetcher=servicenow.fetch_caller_replies,
    reply_assessor=assess_user_reply,
):
    tools = ToolExecutor()
    runner = AgentRunner(tools)
    triage = TriageAgent(runner)
    diagnosis = DiagnosisAgent(runner)
    if awaiting_state is None:
        awaiting_state = os.getenv("SN_AWAITING_USER_INFO_STATE") or None
    if in_progress_state is None:
        in_progress_state = os.getenv("SN_IN_PROGRESS_STATE") or None
    communication = CommunicationAgent(
        runner, channels=communication_channels, awaiting_state=awaiting_state,
        action='request_information',
    )
    communication_start = CommunicationAgent(
        runner, in_progress_state=in_progress_state, action="start_work",
    )
    register_tools(tools, overrides={
        **(c2c_tools or {}),
        'fetch_incident': incident_fetcher, 'fetch_caller_replies': caller_reply_fetcher,
        'list_screenshots': screenshot_lister, 'update_incident': ticket_updater,
        'fetch_caller_global_id': caller_global_id_fetcher,
        'resolve_c2c_student': student_resolver or partial(resolve_c2c_student, execute_tool=runner.execute_tool),
        'read_incident_screenshots': screenshot_reader, 'diagnosis_scenarios': scenario_lookup,
        'classify_incident': classifier, 'analyze_request': partial(analyze_request, assessor=reply_assessor),
        'next_diagnosis_action': diagnosis_reasoner or diagnosis.next_action,
        'compose_communication': communication_reasoner or communication.compose,
    }, mcp_sessions=mcp_sessions)
    nodes = {
        "communication_start": create_agent_node("communication_start", communication_start, runner),
        "triage": create_agent_node("triage", triage, runner),
        "diagnosis": create_agent_node("diagnosis", diagnosis, runner),
        "communication": create_agent_node("communication", communication, runner),
    }
    graph = build_graph(
        state_schema=IncidentState,
        nodes=nodes,
        checkpointer=checkpointer,
    )

    orchestrator = Orchestrator(graph)
    orchestrator.runner = runner
    orchestrator.triage = triage
    return orchestrator
