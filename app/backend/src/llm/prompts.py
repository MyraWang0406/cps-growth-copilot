"""Prompt templates for LLM."""
import json
from typing import Dict, Any


def get_diagnosis_prompt(entity_type: str, entity_id: int, metrics: Dict[str, Any], window: str) -> str:
    """Generate diagnosis prompt."""
    return f"""Analyze the performance of {entity_type} {entity_id} over the past {window}.

Metrics:
{json.dumps(metrics, indent=2, default=str)}

Generate a diagnosis report with:
1. Summary of performance
2. Key insights (opportunities, trends)
3. Risks identified
4. Recommended next actions

Format as JSON matching the DiagnosisReport schema."""


def get_opportunities_prompt(entity_type: str, entity_id: int, metrics: Dict[str, Any], window: str) -> str:
    """Generate opportunities prompt."""
    return f"""Identify growth opportunities for {entity_type} {entity_id} over the past {window}.

Metrics:
{json.dumps(metrics, indent=2, default=str)}

Generate opportunities with:
- Impact (high/medium/low)
- Effort (high/medium/low)
- Estimated gain
- Evidence
- Action items

Format as JSON matching the OpportunitiesResponse schema."""

