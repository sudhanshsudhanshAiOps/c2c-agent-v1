# Provide the asynchronous incident queue consumed by the background worker.
import asyncio

class IncidentQueue:
    # Initialize IncidentQueue with its dependencies and configuration.
    def __init__(self, maxsize: int = 100):
        self._queue = asyncio.Queue(maxsize=maxsize)

    # Add an incident to the asynchronous processing queue.
    async def publish(self, incident: dict):
        self._queue.put_nowait(incident)

    # Wait for and return the next queued incident.
    async def consume(self):
        return await self._queue.get()

    # Mark one queued incident as fully processed.
    def task_done(self):
        self._queue.task_done()

    # Return the current number of queued incidents.
    def size(self):
        return self._queue.qsize()
    
    # Report whether the incident queue currently contains no work.
    def is_empty(self):
        return self._queue.empty()

incident_queue = IncidentQueue()