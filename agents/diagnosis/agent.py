# Investigate incidents through bounded LLM turns, selective SOP loading and tool evidence.
import json
import logging
import os
import re

from core import AgentResult, BaseAgent
from .llm_client import next_action
from .prompts import SYSTEM_PROMPT
from .validation import collect_facts
from .tool_schema import function_schemas, result_entities, validate_call
from tools.request_analyser import REQUESTS, request_key

logger = logging.getLogger(__name__)


class DiagnosisAgent(BaseAgent):
    # Initialize DiagnosisAgent with its dependencies and configuration.
    def __init__(self, runner):
        self.runner = runner
        self.max_iterations = int(os.getenv("DIAGNOSIS_MAX_ITERATIONS", "10"))
        if self.max_iterations < 1:
            raise ValueError("DIAGNOSIS_MAX_ITERATIONS must be a positive integer")
        self.timeout_seconds = self.max_iterations * 90 + 30

    # Invoke the Diagnosis-owned LLM to select its next native tool call.
    def next_action(self, messages, tools):
        return next_action(messages, tools)

    # Investigate verified evidence with bounded model turns and return an evidence-grounded diagnosis.
    async def execute(self, context):
        identity = context.evidence.get("caller_identity") or {}
        incident = context.evidence.get("incident") or {}
        if identity.get("status") != "matched" or not identity.get("studentID") or not incident:
            return AgentResult(status="diagnosis_needs_review", output={
                "diagnosis": {"status": "triage_evidence_missing"}, "next_action": "review_triage"})
        try:
            graph = await self.runner.execute_tool("diagnosis_scenarios", {"category": context.state.get("category")})
            if not graph or not graph.get("scenarios"):
                raise ValueError("No KG scenarios")
            guidance = await self.runner.execute_tool("load_category_skill", {"issue_id": graph["issue_id"]})
        except Exception as error:
            return AgentResult(status="diagnosis_unavailable", error=type(error).__name__, output={
                "diagnosis": {"status": "knowledge_unavailable"}, "next_action": "review_diagnosis"})

        evidence = "\n".join(f"{key}: {incident.get(key) or ''}" for key in ("short_description", "description"))
        evidence += "\nScreenshot OCR: " + " ".join(item.get("text", "") for item in
            context.evidence.get("screenshots", {}).get("screenshots", []) if item.get("status") == "read")
        evidence += "\nNew caller replies (untrusted): " + "\n".join(
            row.get('value', '')[:1000] for row in context.evidence.get('caller_replies', [])[-8:])
        evidence += '\nIncident journal context (untrusted, bot notes are not user confirmation):\n' + '\n'.join(
            str(incident.get(key) or '')[:3000] for key in ('comments', 'work_notes'))
        evidence = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email]", evidence)
        registry = self.runner.describe_tools("diagnosis")
        known_scenarios = [s["scenario_id"] for s in graph["scenarios"]]
        schemas = self.runner.filter_tool_schemas(function_schemas(registry, known_scenarios, guidance["content"]))
        previous = context.state.get("previous_diagnosis") or {}
        if previous.get("category") != context.state.get("category"):
            previous = {}
        if previous:
            logger.info("[%s] Diagnosis prior findings: status=%s checks=%s candidates=%s",
                        context.state["incident_number"], previous.get("status"), len(previous.get("checks", [])),
                        [item.get("scenario_id") for item in previous.get("candidate_scenarios", [])])
        messages = [{"role": "system", "content": SYSTEM_PROMPT + guidance["rules"]}, {"role": "user", "content": json.dumps({"evidence": evidence, "verified_studentID": identity["studentID"],
            "knowledge_graph": [{"scenario_id": s["scenario_id"], "symptom": s["scenario_name"],
                "checks": [v["name"] for v in s.get("validations", [])],
                "apis": [a["name"] for a in s.get("apis", [])]} for s in graph["scenarios"]],
            "previous_diagnosis": previous, "max_iterations": self.max_iterations}, separators=(",", ":"))}]
        checks, facts, selected = [], [], set()
        queried_items = set()
        confirmed_courses = set()
        discovered, cache = {}, {}
        loaded_skills = set()
        interpretation = None
        stop_reason, error_type, tokens = "iteration_limit", None, 0
        input_tokens = output_tokens = cached_tokens = 0
        iterations = 0
        for iteration in range(1, self.max_iterations + 1):
            iterations = iteration
            logger.info("[%s] Diagnosis iteration %s/%s", context.state["incident_number"], iteration, self.max_iterations)
            try:
                # This registered tool invokes the LLM with native function schemas.
                action = await self.runner.execute_tool("next_diagnosis_action", {"messages": messages, "tools": schemas})
                tokens += int(action.get("total_tokens") or 0)
                input_tokens += int(action.get("prompt_tokens") or 0)
                output_tokens += int(action.get("completion_tokens") or 0)
                cached_tokens += int(action.get("cached_tokens") or 0)
                logger.info("[%s] Model usage: input=%s output=%s cached_input=%s total=%s", context.state["incident_number"],
                            action.get("prompt_tokens", 0), action.get("completion_tokens", 0),
                            action.get("cached_tokens", 0), action.get("total_tokens", 0))
            except Exception as error:
                stop_reason, error_type = "model_unavailable", type(error).__name__
                break
            calls = action.get("tool_calls") or []
            assistant = {"role": "assistant", "content": action.get("content") or ""}
            if calls:
                assistant["tool_calls"] = calls
            messages.append(assistant)
            if not calls:
                messages.append({"role": "user", "content": "Use a registered function or finish_diagnosis; a prose answer does not execute checks."})
                continue
            # Return a result for every native tool-call ID, even when the turn is invalid.
            for call in calls:
                function = call.get("function", {})
                name = function.get("name")
                observation = {"status": "invalid_arguments"}
                try:
                    if len(calls) != 1:
                        raise ValueError("Request exactly one function per iteration")
                    arguments = json.loads(function.get("arguments", ""))
                    if not isinstance(arguments, dict):
                        raise ValueError("Function arguments must be an object")
                    if name == 'load_scenario_skill':
                        scenario = arguments.get('scenario_id')
                        if set(arguments) != {'scenario_id'} or scenario not in known_scenarios:
                            raise ValueError('Select a scenario from the current category KG')
                        if scenario in loaded_skills:
                            observation = {'status': 'already_loaded', 'scenario_id': scenario}
                        else:
                            observation = await self.runner.execute_tool(name, {
                                'issue_id': graph['issue_id'], 'scenario_id': scenario})
                            loaded_skills.add(scenario)
                            logger.info('[%s] Diagnosis SOP loaded: scenario=%s', context.state['incident_number'], scenario)
                        messages.append({'role': 'tool', 'tool_call_id': call['id'],
                                         'content': json.dumps(observation, separators=(',', ':'))})
                        continue
                    if name == "finish_diagnosis":
                        if any(isinstance(v, dict) and v.get('status') in ('supported', 'not_supported') and
                               v.get('scenario_id') not in loaded_skills for v in arguments.get('scenario_verdicts', [])):
                            raise ValueError('Load the scenario SOP before confirming or rejecting its cause')
                        interpretation = await self.runner.execute_tool("finish_diagnosis", {"result": arguments,
                            "guidance": guidance["content"], "scenario_ids": known_scenarios, "facts": facts,
                            "confirmed_courses": sorted(confirmed_courses) if len(queried_items) <= 1 else []})
                        selected = set(arguments["scenario_ids"])
                        stop_reason = "finished"
                        break
                    params = validate_call(name, arguments, registry, known_scenarios, identity["studentID"], evidence, discovered)
                    if params.get('itemID') or params.get('componentID'):
                        queried_items.add(params.get('itemID') or params['componentID'])
                    scenario = arguments["scenario_id"]
                    selected.add(scenario)
                    check = {"check_id": f"C{len(checks) + 1}", "scenario_id": scenario, "tool": name, "iteration": iteration,
                             "argument_fields": sorted(params)}
                    logger.info("[%s] Diagnosis requested tool=%s scenario=%s fields=%s", context.state["incident_number"], name, scenario, sorted(params))
                    signature = (name, tuple(sorted(params.items())))
                    if signature in cache:
                        observation = {**cache[signature], "cached": True}
                    else:
                        observation = await self._read(name, params, check["check_id"], identity["studentID"], facts, discovered)
                        cache[signature] = observation
                    if observation['status'] == 'returned_data':
                        course = params.get('itemID') or params.get('componentID')
                        if course:
                            confirmed_courses.add(course)
                        elif params.get('title'):
                            matches = {row['itemID'] for row in observation.get('entities', []) if row.get('itemID')}
                            if len(matches) == 1:
                                confirmed_courses.update(matches)
                    check.update({key: observation[key] for key in ("status", "http_status", "error_type", "cached") if key in observation})
                    checks.append(check)
                    logger.info("[%s] Diagnosis observation: tool=%s status=%s http_status=%s", context.state["incident_number"], name, observation["status"], observation.get("http_status"))
                except (ValueError, TypeError, KeyError) as error:
                    observation = {"status": "invalid_arguments", "message": str(error)[:250]}
                    logger.info("[%s] Diagnosis rejected tool request: tool=%s reason=%s",
                                context.state["incident_number"], name, str(error)[:250])
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(observation, separators=(",", ":"))})
            if interpretation is not None:
                break

        if interpretation is None:
            interpretation = {"status": "needs_more_evidence" if not error_type else "needs_human_review", "subcategory": None,
                "confidence": "low", "missing_evidence": ["api_fields" if facts else "api_data"],
                "scenario_verdicts": [{"scenario_id": s, "status": "needs_more_evidence", "evidence_ids": []} for s in sorted(selected)]}
        verdicts = {v["scenario_id"]: v for v in interpretation["scenario_verdicts"]}
        candidates = [{**{key: s[key] for key in ("scenario_id", "root_cause_ids", "validation_ids", "api_ids", "resolution_ids")},
                       "status": verdicts[s["scenario_id"]]["status"]} for s in graph["scenarios"] if s["scenario_id"] in selected]
        referenced = {ref for v in interpretation["scenario_verdicts"] for ref in v["evidence_ids"]}
        interpretation["evidence_refs"] = [{key: fact[key] for key in ("id", "check_id", "path")} for fact in facts if fact["id"] in referenced]
        logger.info("[%s] Diagnosis conclusion: status=%s subissue=%s stop_reason=%s iterations=%s/%s", context.state["incident_number"],
                    interpretation["status"], interpretation["subcategory"], stop_reason, iterations, self.max_iterations)
        user_requests = []
        for kind in interpretation.get('missing_evidence', []):
            if kind in REQUESTS:
                targets = sorted(queried_items) if kind == 'completion_proof' and queried_items else ['']
                user_requests.extend(request_key(kind, target) for target in targets)
        return AgentResult(status="diagnosis_" + interpretation["status"], error=error_type, output={
            'user_requests': user_requests,
            "knowledge_graph_issue": {"id": graph["issue_id"]}, "knowledge_graph_status": "found",
            "diagnosis": {"status": interpretation["status"], "category": context.state.get("category"),
                "interpretation": interpretation,
                "identity_status": "matched", "skill": guidance["name"], "candidate_scenarios": candidates,
                "checks": checks, "validation_status": interpretation["status"], "iterations": iterations,
                "max_iterations": self.max_iterations, "stop_reason": stop_reason, "model_tokens": tokens,
                "token_usage": {"input": input_tokens, "output": output_tokens, "cached_input": cached_tokens, "total": tokens}},
            "next_action": "review_diagnosis"})

    # Execute a diagnostic read, check learner and course scope, and extract bounded facts and identifiers.
    async def _read(self, name, params, check_id, student_id, facts, discovered):
        try:
            data = await self.runner.execute_tool(name, {"query_params": params})
            rows = data.get("value", data) if isinstance(data, dict) else data
            records = rows if isinstance(rows, list) else [rows] if isinstance(rows, dict) else []
            if any(isinstance(row, dict) and row.get("studentID", student_id) not in (None, student_id) for row in records):
                return {"status": "scope_mismatch", "message": "Response contains another learner; try a supported learner filter."}
            item = params.get("itemID", params.get("componentID"))
            if item and any(isinstance(row, dict) and row.get("itemID", row.get("itemID_ci", row.get("componentID", item))) != item for row in records):
                return {"status": "scope_mismatch", "message": "Response contains another course; use the documented item filter."}
            curricula = params.get("curriculaID")
            if curricula and any(isinstance(row, dict) and row.get("curriculaID", curricula) != curricula for row in records):
                return {"status": "scope_mismatch", "message": "Response contains another curriculum; use the documented curriculum filter."}
            fresh = [{"id": f"F{len(facts) + index + 1}", **fact} for index, fact in enumerate(collect_facts(data, check_id))] if rows else []
            facts.extend(fresh)
            entities = result_entities(data, student_id)
            for entity in entities:
                for key, value in entity.items():
                    aliases = {"itemID": ("itemID", "componentID"), "componentID": ("itemID", "componentID"),
                               "curriculaID": ("curriculaID", "curriculumID"), "curriculumID": ("curriculaID", "curriculumID")}.get(key, (key,))
                    for alias in aliases:
                        discovered.setdefault(alias, set()).add(value)
            return {"status": "returned_data" if rows else "empty_response",
                    "facts": [{"id": f["id"], "field": ".".join(map(str, f["path"])), "value": f["value"]} for f in fresh],
                    "entities": entities}
        except Exception as error:
            return {"status": "unavailable", "error_type": type(error).__name__,
                    "http_status": getattr(getattr(error, "response", None), "status_code", None)}
