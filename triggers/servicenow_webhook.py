# Validate incoming ServiceNow incident events and enqueue them for processing.
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from workers import incident_queue
import asyncio
from runtime import incident_scope

router = APIRouter(prefix="/webhook")

load_dotenv()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
ASSIGNMENT_GROUP = os.getenv("ASSIGNMENT_GROUP", "TCS-BDX-ITLEARNING")

logger = logging.getLogger(__name__)


class IncidentPayload(BaseModel):
    number: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    sys_id: str = Field(pattern=r"^[0-9a-fA-F]{32}$")
    assignment_group: Optional[str] = None
    caller: str
    summary: str
    description: Optional[str] = None
    rediagnose_requested: bool = False
    retriage_requested: bool = False


# Validate the incident webhook, log its receipt and publish it to the worker queue.
@router.post("/incident")
async def receive_incident(
    request: Request,
    payload: IncidentPayload,
    background_tasks: BackgroundTasks,
):
    secret = request.headers.get("X-Webhook-Secret", "")
    if secret != WEBHOOK_SECRET:
        logger.warning(f"Rejected webhook — invalid secret from {request.client.host}")
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    if payload.assignment_group != ASSIGNMENT_GROUP:
        logger.info("Incident ignored: %s (assignment group mismatch)", payload.number)
        return {"status": "ignored", "reason": "assignment group mismatch"}

    # Add this incident in worker queue.
    with incident_scope(payload.number):
        logger.info("Incident received: %s", payload.number)
        try:
            await incident_queue.publish({
                "number": payload.number, "sys_id": payload.sys_id,
                "rediagnose_requested": payload.rediagnose_requested,
                "retriage_requested": payload.retriage_requested,
            })
        except asyncio.QueueFull:
            logger.warning("[%s] Waiting: incident queue is full; retry required", payload.number)
            raise HTTPException(status_code=503, detail="Incident queue is full. Please try again later.")
        logger.info("[%s] Queued: waiting for incident worker", payload.number)

    return {
        "status": "accepted",
        "incident": payload.number,
        "received_at": datetime.now().isoformat(),
        "queue_size": incident_queue.size(),
    }



