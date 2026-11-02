# Single application tool catalog; implementations and LLMs stay with their owners.
"""Single application tool catalog; implementations and LLMs stay with their owners."""
from copy import deepcopy
from functools import partial
from importlib import import_module
import inspect


# Build descriptions and strict query schemas for the supported C2C read tools.
def _c2c_specs():
    result = {}
    user = {"studentID": ["studentID"]}
    item = {"itemID": ["itemID"]}
    curriculum = {"curriculumID": ["curriculumID"]}
    descriptions = {
        "studentID": "Triage-verified learner ID",
        "itemID": "Exact course item ID; a returned itemID_ci can supply this value",
        "componentID": "Exact learning-history component ID for the course",
        "itemTypeID": "Item type ID returned by item search or learning plan",
        "curriculaID": "Curriculum ID returned by a curriculum item read",
        "curriculumID": "Exact curriculum ID",
        "scheduleID": "Scheduled offering ID returned by an earlier read",
    }
    specs = [
        ("fetch_students", "Search a learner record and LMS account status.", user, ["studentID"]),
        ("fetch_user_information", "Read detailed LMS profile and account attributes, not authoritative Workday status.", user, ["studentID"]),
        ("fetch_user_todo_learning_items", "Read assigned learning items, launch and completion context.", {**user, **item}, ["studentID"]),
        ("fetch_learning_item_details", "Read course content, launch and completion configuration.", item, ["itemID"]),
        ("fetch_items", "Check item existence and availability.", item, ["itemID"]),
        ("fetch_catalog_items", "Read catalog visibility and item library association.", item, ["itemID"]),
        ("fetch_curriculum_statuses", "Read learner curriculum assignment status.", {**user, **curriculum}, ["studentID"]),
        ("fetch_curriculum_item_statuses", "List items in a curriculum or check one item's status.", {"curriculaID": ["curriculumID"], **item}, ["curriculaID"]),
        ("fetch_scheduled_offerings", "Read course class sessions and scheduled offerings.", item, ["itemID"]),
        ("fetch_enrollment_listings", "Read learner enrollment and scheduled-session enrollment status.", {**user, "scheduleID": ["scheduleID"]}, ["studentID"]),
        ("fetch_learning_history", "Read learner completion and transcript records; componentID narrows to a course.", {**user, "componentID": ["componentID", "itemID"]}, ["studentID"]),
        ("fetch_curricula", "Look up curriculum configuration.", curriculum, ["curriculumID"]),
    ]
    for name, purpose, fields, required in specs:
        properties = {key: {"type": "string", "minLength": 1, "maxLength": 200,
                            "description": descriptions.get(key, key)}
                      for key in fields}
        alternatives = None
        if name in {"fetch_items", "fetch_catalog_items"}:
            properties["title"] = {"type": "string", "minLength": 3, "maxLength": 200, "description": "Exact course title"}
            required, alternatives = [], [{"required": ["itemID"]}, {"required": ["title"]}]
        if name in {"fetch_learning_item_details", "fetch_items"}:
            properties["itemTypeID"] = {"type": "string", "minLength": 1, "maxLength": 200, "description": "Item type from search result"}
        if name == "fetch_scheduled_offerings":
            properties["scheduleID"] = {"type": "string", "minLength": 1, "maxLength": 200, "description": "Offering ID"}
            required, alternatives = [], [{"required": ["itemID"]}, {"required": ["scheduleID"]}]
        if name == "fetch_curricula":
            properties["curriculumTitle"] = {"type": "string", "minLength": 3, "maxLength": 200, "description": "Exact curriculum title"}
            required, alternatives = [], [{"required": ["curriculumID"]}, {"required": ["curriculumTitle"]}]
        user_alias = {"fetch_user_todo_learning_items": "criteria/targetUserID",
                      "fetch_learning_history": "criteria/targetUserID",
                      "fetch_curriculum_statuses": "csCriteria/targetUserID"}.get(name)
        if user_alias:
            properties[user_alias] = {"type": "string", "description": "Verified learner ID (alternate filter)"}
            required, alternatives = [], [{"required": ["studentID"]}, {"required": [user_alias]}]
        query_schema = {"type": "object", "properties": properties, "required": required, "additionalProperties": False}
        if alternatives:
            query_schema["anyOf"] = alternatives
        result[name] = {'handler': 'mcp_servers.c2c.client:' + name, 'mcp': 'c2c', 'definition': {
            "scope": "diagnosis", "description": purpose, "method": "GET",
            "parameters": {"type": "object", "properties": {"query_params": query_schema},
                           "required": ["query_params"], "additionalProperties": False},
        }}
    return result


# Names, ownership and transport are defined here once. Imports are resolved only
# when tools are bound, avoiding agent/runtime import cycles.
_FIXED = {
    'resolve_c2c_student': ('tools.identity_verification:resolve_c2c_student', None, 'triage', 'Resolve one verified learner.'),
    'fetch_incident': ('mcp_servers.servicenow.client:fetch_incident_by_sys_id', 'servicenow', 'servicenow', 'Read the incident and journal context.'),
    'fetch_caller_global_id': ('mcp_servers.servicenow.client:fetch_caller_global_id', 'servicenow', 'servicenow', 'Read the caller shared identity.'),
    'list_screenshots': ('mcp_servers.servicenow.client:list_screenshots', 'servicenow', 'servicenow', 'List incident screenshots.'),
    'read_incident_screenshots': ('tools.screenshot_reader:read_incident_screenshots', 'servicenow', 'servicenow', 'Read screenshot OCR.'),
    'fetch_caller_replies': ('mcp_servers.servicenow.client:fetch_caller_replies', 'servicenow', 'servicenow', 'Read recent verified caller comments.'),
    'update_incident': ('mcp_servers.servicenow.client:update_incident', 'servicenow', 'servicenow', 'Apply selected incident fields.'),
    'classify_incident': ('tools.classifier:classify_incident', None, 'triage', 'Classify the incident.'),
    'analyze_request': ('tools.request_analyser:analyze_request', None, 'triage', 'Assess requested user evidence.'),
    'diagnosis_scenarios': ('tools.knowledge_graph:diagnosis_scenarios', None, 'internal', 'Read category KG scenarios.'),
    'load_category_skill': ('tools.skill_loader:load_category_skill', None, 'internal', 'Load category SOP rules.'),
    'load_scenario_skill': ('tools.skill_loader:load_scenario_skill', None, 'diagnosis', 'Load detailed SOP checks and decision rules for one candidate scenario.'),
    'load_communication_skill': ('tools.skill_loader:load_communication_skill', None, 'internal', 'Load communication guidance.'),
    'finish_diagnosis': ('agents.diagnosis.validation:finish_diagnosis', None, 'internal', 'Validate the final diagnosis.'),
    'next_diagnosis_action': (None, None, 'internal', 'Invoke the Diagnosis agent-owned model.'),
    'compose_communication': (None, None, 'communication', 'Invoke the Communication agent-owned model.'),
}


# Combine C2C reads and local operations into the shared tool catalog.
def tool_specs():
    result = _c2c_specs()
    result.update({name: {'handler': handler, 'mcp': server, 'definition': {
        'scope': scope, 'description': description}}
        for name, (handler, server, scope, description) in _FIXED.items()})
    result['resolve_c2c_student']['definition']['parameters'] = {
        'type': 'object', 'properties': {'global_id': {'type': 'string'}},
        'required': ['global_id'], 'additionalProperties': False,
    }
    return result


# Projection for MCP connection checks, not a second registry.
def gateway_tools():
    """Projection for MCP connection checks, not a second registry."""
    specs = tool_specs()
    return {server: tuple(name for name, spec in specs.items() if spec['mcp'] == server)
            for server in ('c2c', 'servicenow')}


# Resolve a catalog module-and-attribute path to its Python callable.
def _resolve(path):
    module, name = path.split(':', 1)
    return getattr(import_module(module), name)


# Infer an object parameter schema from a callable signature.
def _parameters(handler):
    properties, required = {}, []
    for name, parameter in inspect.signature(handler).parameters.items():
        if parameter.kind in (parameter.VAR_KEYWORD, parameter.VAR_POSITIONAL):
            continue
        types = {str: 'string', bool: 'boolean', int: 'integer', float: 'number',
                 dict: 'object', list: 'array'}
        kind = types.get(parameter.annotation)
        properties[name] = {'type': kind} if kind else {}
        if parameter.default is parameter.empty:
            required.append(name)
    return {'type': 'object', 'properties': properties, 'required': required, 'additionalProperties': False}


# Bind one catalog; overrides preserve test injection and agent-owned LLMs.
def register_tools(executor, *, overrides=None, mcp_sessions=None, scope=None):
    """Bind one catalog; overrides preserve test injection and agent-owned LLMs."""
    overrides, sessions = overrides or {}, mcp_sessions or {}
    specs = tool_specs()
    unknown = set(overrides) - set(specs)
    if unknown:
        raise ValueError('Unknown tool override: ' + ', '.join(sorted(unknown)))
    for server, session in sessions.items():
        if server not in gateway_tools():
            raise ValueError('Unknown MCP server')
        executor.register_mcp(server, session)
    for name, spec in specs.items():
        definition = deepcopy(spec['definition'])
        if scope is not None and definition['scope'] != scope:
            continue
        original = _resolve(spec['handler']) if spec['handler'] else None
        handler = overrides.get(name, original)
        if name == 'resolve_c2c_student' and name not in overrides:
            handler = partial(handler, execute_tool=executor.execute)
        if handler is None:
            raise ValueError('Agent-owned callback required for ' + name)
        if 'parameters' not in definition:
            definition['parameters'] = _parameters(original or handler)
        executor.register_local(name, handler, description=definition)
        if spec['mcp'] in sessions:
            executor.register_remote(name, spec['mcp'])
