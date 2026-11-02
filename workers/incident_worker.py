# Consume queued incidents and run their checkpointed workflows.
import asyncio
import logging 
from workers import incident_queue
from runtime import incident_scope

logger = logging.getLogger(__name__)

class IncidentWorker:
    # Initialize IncidentWorker with its dependencies and configuration.
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    # Consume queued incidents, run their workflows and log completion or failure.
    async def start(self):
        logger.info(f"Incident Worker Started")

        while True:
            incident = await incident_queue.consume()
            with incident_scope(incident["number"]):
                try:
                    logger.info("[%s] Worker: processing incident", incident["number"])
                    initial = {"sys_id": incident["sys_id"], "incident_number": incident["number"], "events": []}
                    for flag in ("rediagnose_requested", "retriage_requested"):
                        if incident.get(flag):
                            initial[flag] = True
                    result = await self.orchestrator.run(
                        incident_id=incident["sys_id"],
                        initial_state=initial,
                    )
                    logger.info("[%s] Workflow finished | Stage: %s | Category: %s | Status: %s | Next: %s",
                                incident["number"], result.get("current_stage"), result.get("category"),
                                result.get("workflow_status"), result.get("next_action"))
                except asyncio.CancelledError:
                    logger.info("[%s] Incident worker cancelled", incident["number"])
                    raise
                except Exception as error:
                    logger.error("[%s] Workflow failed: %s; review required", incident["number"], type(error).__name__)
                finally:
                    incident_queue.task_done()
