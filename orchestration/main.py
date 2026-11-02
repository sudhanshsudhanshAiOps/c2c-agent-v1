# Start the FastAPI webhook service, incident worker and shared MCP connections.

import os
import asyncio
import logging

if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from runtime import checkpoint_saver, configure_logging, connect_mcp_servers

from triggers import servicenow_router
from workers import IncidentWorker
from orchestration import create_orchestrator

load_dotenv()

logger = logging.getLogger(__name__)


# Open checkpoint and MCP resources, start the worker, and clean them up on shutdown.
@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    async with checkpoint_saver() as checkpointer, connect_mcp_servers() as sessions:
        orchestrator = create_orchestrator(checkpointer=checkpointer, mcp_sessions=sessions)
        worker_task = asyncio.create_task(IncidentWorker(orchestrator).start())
        logger.info("Incident worker started")

        try:
            yield
        finally:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
            logger.info("Incident worker stopped")


app = FastAPI(
    title="C2C Agentic Resolution",
    version="1.0.0",
    lifespan=lifespan,
)

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(servicenow_router)


# Return the service health response.
@api_v1_router.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(api_v1_router)


if __name__ == "__main__":
    import uvicorn

    configure_logging()
    port = int(os.getenv("WEBHOOK_PORT", "8000"))

    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_config=None, access_log=False)
    server = uvicorn.Server(config)
    if os.name == "nt":
        asyncio.run(server.serve(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(server.serve())
