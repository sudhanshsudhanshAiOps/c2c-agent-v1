# Wrap agents as graph nodes, log findings and maintain pending request state.
import logging
from tools.request_analyser import build_request

logger = logging.getLogger(__name__)


# Build a graph node that runs one agent and applies its findings and request-state changes.
def create_agent_node(agent_name, agent, runner):

    # Run the selected agent, log its findings and produce the next checkpoint update.
    async def node(state):
        number = state.get("incident_number", state.get("sys_id"))
        logger.info("[%s] Agent started: %s", number, agent_name.replace("_", " ").title())
        result = await runner.run(
            agent=agent,
            context=state
        )

        if agent_name == "triage":
            decision = result.output.get("triage") or state.get("triage") or {}
            logger.info("[%s] Triage findings: category=%s confidence=%s identity=%s screenshot=%s classification=%s",
                        number, result.output.get("category", state.get("category")), decision.get("confidence"),
                        result.output.get("caller_identity", {}).get("status"),
                        result.output.get("screenshot_ocr", {}).get("status"), result.status)
        elif agent_name == "diagnosis":
            diagnosis = result.output.get("diagnosis", {})
            logger.info("[%s] Diagnosis findings: skill=%s candidates=%s validation=%s",
                        number, diagnosis.get("skill"),
                        [item["scenario_id"] for item in diagnosis.get("candidate_scenarios", [])],
                        diagnosis.get("validation_status", diagnosis.get("status")))
            interpretation = diagnosis.get("interpretation") or {}
            missing = interpretation.get("missing_evidence")
            logger.info("[%s] Subcategory: %s", number, interpretation.get("subcategory") or "Unconfirmed")
            logger.info("[%s] Confidence: %s", number, interpretation.get("confidence") or "Not evaluated")
            logger.info("[%s] Missing evidence: %s", number,
                        "Not evaluated" if missing is None else ", ".join(x.replace("_", " ") for x in missing) or "None")
            if missing:
                logger.info("[%s] Diagnosis waiting for: %s", number, ", ".join(x.replace("_", " ") for x in missing))
            for check in diagnosis.get("checks", []):
                logger.info("[%s] Diagnosis check: scenario=%s tool=%s result=%s missing_identifiers=%s http_status=%s error=%s",
                            number, check.get("scenario_id"), check.get("tool"),
                            check.get("status"), check.get("missing_identifiers", []), check.get("http_status"), check.get("error_type"))
        logger.info("[%s] Agent finished: %s | Status: %s | Next: %s | Error: %s",
                    number, agent_name.replace("_", " ").title(), result.status.replace("_", " "),
                    (result.output.get("next_action") or "continue").replace("_", " "), result.error)

        update = result.to_state_update(agent_name)
        if result.output.get('clear_user_request'):
            update.update(active_user_request=None, user_request_details=None, user_request_at=None)
        request = result.output.get('request_to_user')
        if agent_name == 'triage' and result.output.get('next_action') == 'request_screenshot':
            request = 'awaiting_screenshot'
        if agent_name == 'diagnosis':
            diagnosis = result.output.get('diagnosis') or {}
            if diagnosis.get('stop_reason') == 'finished' and diagnosis.get('status') == 'needs_more_evidence':
                requests = result.output.get('user_requests', [])
                request = requests[0] if requests else None
                if request: update['next_action'] = 'request_information'
        if request:
            update['active_user_request'] = request
            update['user_request_details'] = (state.get('user_request_details')
                if state.get('active_user_request') == request else None) or build_request(request, agent_name)

        if agent_name == 'diagnosis' or (agent_name == 'communication' and
                result.output.get('next_action') in ('wait_for_screenshot', 'wait_for_user_information')):
            update['processing_update'] = False
        return update

    return node
