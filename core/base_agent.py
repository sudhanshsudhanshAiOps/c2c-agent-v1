# Define the common execution interface implemented by each agent.
from abc import ABC, abstractmethod

from core import IncidentContext
from core import AgentResult


class BaseAgent(ABC):

    # Define the asynchronous execution contract that concrete agents must implement.
    @abstractmethod
    async def execute(
        self,
        context: IncidentContext,
    ) -> AgentResult:
        ...