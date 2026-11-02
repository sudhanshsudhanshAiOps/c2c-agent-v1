# Native function schemas and argument validation for iterative diagnosis.
"""Native function schemas and argument validation for iterative diagnosis."""
from copy import deepcopy
import re

from .validation import MISSING

USER_PARAMETERS = {"studentID", "criteria/targetUserID", "csCriteria/targetUserID"}
ENTITY_PARAMETERS = {"itemID", "componentID", "curriculumID", "curriculaID", "scheduleID", "itemTypeID", "title", "curriculumTitle"}


# Build native LLM schemas for C2C reads, scenario-SOP loading and final diagnosis.
def function_schemas(registry, scenario_ids, guidance):
    functions = []
    # IDs already appear once in the KG context; validate them at execution time.
    scenario = {"type": "string", "description": "KG scenario_id"}
    for name, spec in registry.items():
        if name == 'load_scenario_skill':
            functions.append({'type': 'function', 'function': {'name': name,
                'description': spec['description'], 'parameters': {'type': 'object',
                'properties': {'scenario_id': {'type': 'string', 'enum': scenario_ids}},
                'required': ['scenario_id'], 'additionalProperties': False}}})
            continue
        parameters = deepcopy(spec["parameters"])
        parameters["properties"]["scenario_id"] = scenario
        parameters["required"].append("scenario_id")
        functions.append({"type": "function", "function": {"name": name, "description": spec["description"], "parameters": parameters}})
    labels = [label for label in re.findall(r"^\* `([^`]+)`", guidance, re.M)
              if 'three strikes' not in label.lower()]
    verdict = {"type": "object", "properties": {
        "scenario_id": scenario, "status": {"type": "string", "enum": ["supported", "not_supported", "needs_more_evidence"]},
        "evidence_ids": {"type": "array", "items": {"type": "string"}},
    }, "required": ["scenario_id", "status", "evidence_ids"], "additionalProperties": False}
    properties = {
        "scenario_ids": {"type": "array", "items": scenario, "uniqueItems": True},
        "status": {"type": "string", "enum": ["supported", "needs_more_evidence", "needs_human_review"]},
        "subcategory": {"type": ["string", "null"], "enum": labels + [None]},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "scenario_verdicts": {"type": "array", "items": verdict},
        "missing_evidence": {"type": "array", "items": {"type": "string", "enum": sorted(MISSING)}},
    }
    functions.append({"type": "function", "function": {"name": "finish_diagnosis", "description": "Finish with SOP-based conclusions grounded in observed fact IDs; report missing evidence rather than inventing a cause.",
        "parameters": {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}}})
    return functions


# Check a diagnostic query against its schema, known scenario and verified evidence identifiers.
def validate_call(name, arguments, registry, scenario_ids, student_id, evidence, discovered):
    if name not in registry:
        raise ValueError("Tool is not registered for diagnosis")
    if not isinstance(arguments, dict) or set(arguments) != {"scenario_id", "query_params"}:
        raise ValueError("Expected scenario_id and query_params")
    if arguments["scenario_id"] not in scenario_ids:
        raise ValueError("Unknown KG scenario")
    params = arguments["query_params"]
    schema = registry[name]["parameters"]["properties"]["query_params"]
    if not isinstance(params, dict) or set(params) - set(schema["properties"]):
        raise ValueError("Unsupported query parameters; allowed: " + ", ".join(schema["properties"]))
    if not set(schema["required"]).issubset(params) or (schema.get("anyOf") and not any(set(option["required"]).issubset(params) for option in schema["anyOf"])):
        raise ValueError("Required query parameter missing; consult the tool schema")
    for key, value in params.items():
        prop = schema["properties"][key]
        if not isinstance(value, str) or not prop.get("minLength", 1) <= len(value) <= prop.get("maxLength", 200):
            raise ValueError("Query values must be nonempty strings within schema limits")
        if key in USER_PARAMETERS:
            if value != student_id:
                raise ValueError("Learner parameters must equal the verified studentID")
        elif value not in evidence and value not in discovered.get(key, set()):
            raise ValueError("Query value is absent from incident evidence and prior tool results")
    return params


# Collect bounded course and curriculum identifiers from correctly scoped tool results.
def result_entities(data, student_id):
    entities = []
    # Walk scoped response values and collect reusable course and curriculum identifiers.
    def visit(value):
        if isinstance(value, dict):
            if value.get("studentID", student_id) != student_id:
                return
            entity = {key: child[:200] for key, child in value.items() if key in ENTITY_PARAMETERS and isinstance(child, str)}
            for source, target in (("itemID_ci", "itemID"), ("itemTypeID_ci", "itemTypeID")):
                if target not in entity and isinstance(value.get(source), str):
                    entity[target] = value[source][:200]
            if entity:
                entities.append(entity)
            for child in value.values():
                if isinstance(child, (dict, list)):
                    visit(child)
        elif isinstance(value, list):
            for child in value[:25]:
                visit(child)
    visit(data)
    return entities[:25]
