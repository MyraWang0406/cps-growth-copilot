"""LLM adapter interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any


class LLMAdapter(ABC):
    """Abstract base class for LLM adapters."""

    @abstractmethod
    async def generate_diagnosis(
        self, entity_type: str, entity_id: int, metrics: Dict[str, Any], window: str
    ) -> Dict[str, Any]:
        """Generate diagnosis report."""
        pass

    @abstractmethod
    async def generate_opportunities(
        self, entity_type: str, entity_id: int, metrics: Dict[str, Any], window: str
    ) -> Dict[str, Any]:
        """Generate opportunities."""
        pass

