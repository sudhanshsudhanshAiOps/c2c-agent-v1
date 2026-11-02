# Draft user requests and apply orchestrator-selected ServiceNow updates.
import logging
import os

from core import AgentResult, BaseAgent, IncidentContext
from .llm_client import compose_message
from .messages import screenshot_request, validate_draft
from tools.request_analyser import build_request
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CommunicationAgent(BaseAgent):
    # Initialize CommunicationAgent with its dependencies and configuration.
    def __init__(
        self,
        runner,
        channels: tuple[str, ...] = ("comments", "work_notes"),
        awaiting_state: str | None = None,
        in_progress_state: str | None = None,
        action: str = "request_screenshot",
    ):
        self.runner = runner
        self.channels = channels
        self.awaiting_state = awaiting_state
        self.in_progress_state = in_progress_state
        self.action = action

    # Delegate message wording to the Communication-owned LLM client.
    def compose(self, number, channels, rules, action='request_screenshot', request=None):
        return compose_message(number, channels, rules, action=action, request=request)

    # Communicate the stored pending requirements and record successful contact time.
    async def request_information(self, context):
        key = context.state.get('active_user_request')
        if not key: return AgentResult(status='communication_failed', error='No user request selected')
        number = context.state['incident_number']
        requested = context.state.get('user_request_details') or build_request(key)
        details = '; '.join(requested['required_information'])
        if requested.get('target_id'):
            details += ' for course/item ' + requested['target_id']
        channels = [channel for channel in self.channels if channel in ('comments', 'work_notes')]
        fields = {channel: f'Incident {number}: please provide {details} so we can investigate.' for channel in channels}
        try:
            skill = await self.runner.execute_tool('load_communication_skill')
            draft = await self.runner.execute_tool('compose_communication', {
                'number': number, 'channels': channels, 'rules': skill['rules'],
                'action': 'request_information', 'request': requested})
            fields.update(validate_draft(draft, number, channels, require_screenshot=False))
        except Exception as error:
            logger.warning('[%s] Message draft unavailable (%s); using template', number, type(error).__name__)
        if self.awaiting_state: fields['state'] = self.awaiting_state
        try:
            await self.runner.execute_tool('update_incident', {'sys_id': context.incident_id, 'fields': fields})
        except Exception as error:
            return AgentResult(status='communication_failed', error=type(error).__name__,
                               output={'next_action': 'retry_communication'})
        return AgentResult(status='awaiting_user_information', output={
            'active_user_request': key, 'user_request_at': datetime.now(timezone.utc).isoformat(),
            'next_action': 'wait_for_screenshot' if key == 'awaiting_screenshot' else 'wait_for_user_information'})

    # Perform the selected status update or user-information communication action.
    async def execute(self, context: IncidentContext) -> AgentResult:
        previous = context.state.get("communication") or {}
        if self.action == "start_work":
            incident = context.evidence.get('incident') or {}
            if (
                not incident
                or incident.get("sys_id") != context.incident_id
                or incident.get("number") != context.state["incident_number"]
            ):
                return AgentResult(status="incident_unavailable",
                                   error="Incident identity does not match webhook",
                                   output={"next_action": "retry_incident_fetch"})

            if not self.in_progress_state:
                return AgentResult(status="communication_failed", error="SN_IN_PROGRESS_STATE is not configured",
                                   output={"next_action": "configure_in_progress_state"})
            if (str(incident.get('active', '')).lower() == 'false'
                    or str(incident.get('state')) == os.getenv('SN_CLOSED_STATE')):
                return AgentResult(status='incident_closed', output={'next_action': 'end'})
            try:
                await self.runner.execute_tool(
                    "update_incident",
                    {"sys_id": context.incident_id, "fields": {"state": self.in_progress_state}},
                )
            except Exception as error:
                return AgentResult(status="communication_failed", error=type(error).__name__,
                                   output={"next_action": "retry_set_in_progress"})
            return AgentResult(
                status="in_progress",
                output={
                    "communication": {
                        **previous,
                        "in_progress_set": True,
                        "screenshot_request_sent": previous.get("screenshot_request_sent", False),
                    },
                    "next_action": None,
                },
            )

        if self.action == 'request_information':
            return await self.request_information(context)

        if previous.get("screenshot_request_sent"):
            return AgentResult(
                status="awaiting_screenshot",
                output={"communication": previous, "next_action": "wait_for_screenshot"},
            )

        try:
            screenshots = await self.runner.execute_tool(
                "list_screenshots", {"incident_sys_id": context.incident_id}
            )
        except Exception as error:
            return AgentResult(
                status="communication_failed",
                error=type(error).__name__,
                output={"next_action": "retry_screenshot_check"},
            )
        if screenshots:
            return AgentResult(
                status="screenshot_received",
                output={"next_action": "retriage"},
            )

        fields = screenshot_request(context.state["incident_number"], self.channels, self.awaiting_state)
        channels = [channel for channel in self.channels if channel in ("comments", "work_notes")]
        source = "template_fallback"
        if channels:
            try:
                skill = await self.runner.execute_tool("load_communication_skill")
                draft = await self.runner.execute_tool("compose_communication", {
                    "number": context.state["incident_number"], "channels": channels, "rules": skill["rules"],
                })
                fields.update(validate_draft(draft, context.state["incident_number"], channels))
                source = "llm"
            except Exception as error:
                logger.warning("[%s] Communication draft unavailable (%s); using approved template",
                               context.state["incident_number"], type(error).__name__)
        logger.info("[%s] Communication: screenshot request prepared | Source: %s",
                    context.state["incident_number"], source)

        try:
            await self.runner.execute_tool(
                "update_incident", {"sys_id": context.incident_id, "fields": fields}
            )
        except Exception as error:
            return AgentResult(
                status="communication_failed",
                error=type(error).__name__,
                output={"next_action": "retry_request_screenshot"},
            )

        return AgentResult(
            status="awaiting_screenshot",
            output={
                "communication": {
                    **previous,
                    "action": "request_screenshot",
                    "screenshot_request_sent": True,
                    "channels": list(self.channels),
                    "state_updated": self.awaiting_state is not None,
                    "message_source": source,
                },
                "next_action": "wait_for_screenshot",
            },
        )
