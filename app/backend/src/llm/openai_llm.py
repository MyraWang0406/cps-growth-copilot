"""OpenAI LLM adapter (optional)."""
import os
import json
from typing import Dict, Any
from ..llm.adapter import LLMAdapter
from ..llm.prompts import get_diagnosis_prompt, get_opportunities_prompt


class OpenAILLM(LLMAdapter):
    """OpenAI LLM adapter."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")

    async def generate_diagnosis(
        self, entity_type: str, entity_id: int, metrics: Dict[str, Any], window: str
    ) -> Dict[str, Any]:
        """Generate diagnosis using OpenAI."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")

        # This is a placeholder - in production, you would call OpenAI API here
        # For now, fallback to fake_llm logic
        from .fake_llm import FakeLLM
        fake_llm = FakeLLM()
        return await fake_llm.generate_diagnosis(entity_type, entity_id, metrics, window)

    async def generate_opportunities(
        self, entity_type: str, entity_id: int, metrics: Dict[str, Any], window: str
    ) -> Dict[str, Any]:
        """Generate opportunities using OpenAI."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")

        # This is a placeholder - in production, you would call OpenAI API here
        from .fake_llm import FakeLLM
        fake_llm = FakeLLM()
        return await fake_llm.generate_opportunities(entity_type, entity_id, metrics, window)

