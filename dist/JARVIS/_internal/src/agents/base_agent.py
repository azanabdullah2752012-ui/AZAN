from abc import ABC, abstractmethod
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Abstract base class for all AZAN autonomous agents.
    
    Every agent must implement three lifecycle methods:
    - think():  Analyze the context and decide on an approach
    - act():    Execute the decided approach
    - evaluate(): self-evaluate the result quality
    """

    def __init__(self, name: str):
        self.name = name
        logger.info(f"Agent initialized: {self.name}")

    @abstractmethod
    async def think(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze context and produce a plan or decision payload."""

    @abstractmethod
    async def act(self, plan: Dict[str, Any]) -> Any:
        """Execute the plan and return a result."""

    @abstractmethod
    async def evaluate(self, result: Any) -> float:
        """Score the result quality between 0.0 and 1.0."""

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Executes the full think → act → evaluate lifecycle."""
        try:
            plan = await self.think(context)
            logger.debug(f"[{self.name}] Plan: {plan}")
            result = await self.act(plan)
            score = await self.evaluate(result)
            logger.info(f"[{self.name}] Completed with quality score: {score:.2f}")
            return {"result": result, "score": score, "agent": self.name}
        except Exception as e:
            logger.error(f"[{self.name}] Agent run failed: {e}")
            return {"result": None, "score": 0.0, "agent": self.name, "error": str(e)}
