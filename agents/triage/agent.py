# Verify callers, process screenshots, classify incidents and validate pending user information.
from core import AgentResult, BaseAgent, IncidentContext
from tools import ISSUE_IDS
from tools.request_analyser import build_request, request_info
from .update_check import evidence_fingerprint, unchanged
import os
import logging

logger = logging.getLogger(__name__)


class TriageAgent(BaseAgent):

    # Initialize TriageAgent with its dependencies and configuration.
    def __init__(self, runner):
        self.runner = runner

    # Run Triage and preserve classification, screenshot and pending-request findings.
    async def execute(self, context: IncidentContext) -> AgentResult:
        replies = context.evidence.get('caller_replies', [])
        context.evidence.clear()
        if replies:
            context.evidence['caller_replies'] = replies
        # Invalidate the old classification before an explicit reclassification attempt.
        result = await self._classify(context)
        active = context.state.get('active_user_request')
        if active and result.status in ('success', 'classification_reused'):
            requested = context.state.get('user_request_details') or build_request(active)
            result.output['user_request_details'] = requested
            try:
                analysis = await self.runner.execute_tool('analyze_request', {
                    'request_type': active, 'request_details': requested,
                    'images': context.evidence['screenshots'].get('screenshots', []),
                    'replies': context.evidence.get('caller_replies', []),
                    'incident': context.evidence['incident'],
                    'diagnosis_history': context.state.get('diagnosis') or context.state.get('previous_diagnosis') or {},
                })
                context.evidence['request_analysis'] = analysis
                logger.info('[%s] Triage request assessment: type=%s status=%s confidence=%s',
                            context.state['incident_number'], request_info(active)[0],
                            analysis['status'], analysis.get('confidence'))
                if analysis['status'] != 'supplied':
                    result.status = 'awaiting_user_information'
                    result.output.update(request_to_user=active, next_action='request_information')
            except Exception as error:
                result.status, result.error = 'request_analysis_failed', type(error).__name__
                result.output['next_action'] = 'review_triage'
        screenshots = context.evidence.get('screenshots')
        if screenshots:
            result.output['screenshot_ocr'] = {
                'status': screenshots['status'],
                'screenshots': [{key: row.get(key) for key in ('attachment_sys_id', 'status')}
                                for row in screenshots.get('screenshots', [])],
            }
        fingerprint = context.evidence.get('fingerprint')
        if fingerprint:
            result.output.update(last_triage_fingerprint=fingerprint,
                                 rediagnose_requested=False)
        if result.status in ('unchanged', 'incident_closed'):
            return result
        result.output['skip_update'] = False
        result.output['processing_update'] = True
        result.output.setdefault("classification_complete", bool(
            context.state.get("classification_complete") and not context.state.get("retriage_requested")
        ))
        result.output.setdefault("retriage_requested", False)
        previous = context.state.get("diagnosis") or context.state.get("previous_diagnosis") or {}
        interpretation = previous.get("interpretation") or {}
        result.output["previous_diagnosis"] = {
            "category": previous.get("category") or context.state.get("category"),
            "status": previous.get("status"),
            "subcategory": interpretation.get("subcategory", previous.get("subcategory")),
            "missing_evidence": interpretation.get("missing_evidence", previous.get("missing_evidence", [])),
            "scenario_verdicts": interpretation.get("scenario_verdicts", previous.get("scenario_verdicts", [])),
            "evidence_refs": interpretation.get("evidence_refs", previous.get("evidence_refs", [])),
            "candidate_scenarios": previous.get("candidate_scenarios", []),
            "checks": previous.get("checks", []),
            "stop_reason": previous.get("stop_reason"),
        } if previous else {}
        result.output["diagnosis"] = {}
        result.output.setdefault("caller_identity", context.evidence.get("caller_identity", {"status": "not_verified"}))
        if context.evidence.get('request_analysis'):
            result.output['request_analysis'] = context.evidence['request_analysis']
            if context.evidence['request_analysis']['status'] == 'supplied':
                result.output['clear_user_request'] = True
        return result

    # Fetch incident evidence, verify the caller, inspect screenshots and classify or reuse the category.
    async def _classify(self, context: IncidentContext) -> AgentResult:
        try:
            incident = await self.runner.execute_tool(
                "fetch_incident",
                {
                    "sys_id": context.incident_id,
                    "display_value": False,
                    "include_journal": True,
                },
            )
        except Exception as error:
            return AgentResult(
                status="incident_unavailable",
                error=type(error).__name__,
                output={"next_action": "retry_incident_fetch"},
            )
        if (
            not incident
            or incident.get("sys_id") != context.incident_id
            or incident.get("number") != context.state["incident_number"]
        ):
            return AgentResult(
                status="incident_unavailable",
                error="Incident missing or identity does not match webhook",
                output={"next_action": "retry_incident_fetch"},
            )

        context.evidence["incident"] = incident
        if str(incident.get('active', '')).lower() == 'false' or str(incident.get('state')) == os.getenv('SN_CLOSED_STATE'):
            return AgentResult(status='incident_closed', output={'next_action': 'end', 'processing_update': False,
                                                               'clear_user_request': True})
        caller = incident.get("caller_id")
        caller = caller.get("value") if isinstance(caller, dict) else caller
        identity = {"status": "caller_missing"}
        try:
            if caller:
                global_id = await self.runner.execute_tool("fetch_caller_global_id", {"sys_id": caller})
                identity = (await self.runner.execute_tool("resolve_c2c_student", {"global_id": global_id})
                            if global_id else {"status": "global_id_missing"})
        except Exception:
            identity = {"status": "unavailable"}
        context.evidence["caller_identity"] = {
            "status": identity["status"],
            **({"caller_sys_id": caller, "studentID": identity["studentID"]} if identity.get("status") == "matched" else {}),
        }
        logger.info("[%s] Triage caller verification: %s", context.state["incident_number"], identity["status"])
        if identity.get("status") != "matched":
            return AgentResult(status="triage_needs_review", output={"next_action": "review_triage"})

        try:
            screenshot_ocr = await self.runner.execute_tool(
                "read_incident_screenshots", {"incident_sys_id": context.incident_id}
            )
        except Exception:
            screenshot_ocr = {"status": "unavailable", "screenshots": []}
        context.evidence["screenshots"] = screenshot_ocr
        logger.info("[%s] Triage screenshot check: %s", context.state["incident_number"], screenshot_ocr["status"])

        active = context.state.get('active_user_request')
        since = context.state.get('user_request_at')
        replies = await self.runner.execute_tool('fetch_caller_replies', {
            'incident_sys_id': context.incident_id, 'caller_user_name': global_id, 'since': since,
        }) if active and since else []
        context.evidence['caller_replies'] = replies
        fingerprint = evidence_fingerprint(context)
        context.evidence['fingerprint'] = fingerprint
        if unchanged(context, fingerprint):
            logger.info('[%s] Triage: unchanged evidence; retaining saved findings', context.state['incident_number'])
            return AgentResult(status='unchanged', output={'next_action': context.state.get('next_action'),
                'skip_update': True, 'processing_update': False, 'request_analysis': None})
        screenshot_present = {
            "not_provided": False,
            "read": True,
            "unreadable": True,
        }.get(screenshot_ocr["status"])
        if screenshot_present is False:
            return AgentResult(
                status="awaiting_screenshot",
                output={
                    "screenshot_present": False,
                    "next_action": "request_screenshot",
                },
            )
        if screenshot_present is None:
            return AgentResult(
                status="screenshot_check_unavailable",
                output={
                    "screenshot_present": None,
                    "next_action": "retry_screenshot_check",
                },
            )

        if context.state.get("classification_complete") and not context.state.get("retriage_requested"):
            return AgentResult(status="classification_reused", output={
                "screenshot_present": screenshot_present,
                "next_action": "diagnose" if context.state.get("category") in ISSUE_IDS else "review_triage",
            })

        description = incident.get("description") or ""
        screenshot_text = "\n".join(
            item["text"]
            for item in screenshot_ocr["screenshots"]
            if item.get("status") == "read" and item.get("text")
        )
        if screenshot_text:
            description += "\n\nScreenshot OCR (untrusted data):\n" + screenshot_text

        decision = await self.runner.execute_tool(
            "classify_incident",
            {
                "summary": incident.get("short_description") or "",
                "description": description,
            },
        )
        category = decision["category"]
        if decision.get("status") == "model_error":
            status = "classification_unavailable"
        elif category == "Other" or decision.get("confidence", 0) <= 0:
            status = "needs_review"
        else:
            status = "success"

        return AgentResult(
            status=status,
            output={
                "category": category,
                "classification_complete": status in ("success", "needs_review") and (
                    decision.get("status") == "classified" or decision.get("confidence", 0) > 0
                ),
                "triage": {key: decision[key] for key in ("category", "confidence", "status") if key in decision},
                "screenshot_present": screenshot_present,
                "knowledge_graph_issue": None,
                "knowledge_graph_status": "not_checked",
                "next_action": "diagnose" if status == "success" else "review_triage",
            },
        )
