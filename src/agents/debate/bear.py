"""Bear-side debate researcher agent."""

from __future__ import annotations

import logging

from src.agents.llm.router import LLMRouter
from src.schemas import DebateRound

logger = logging.getLogger(__name__)


class BearResearcher:
    """Builds anti-investment arguments from risk evidence."""

    def __init__(self, llm_router: LLMRouter | None = None) -> None:
        self._llm = llm_router

    def argue(
        self,
        company_name: str,
        industry: str,
        evidence: list[str],
        attack_points: list[str] | None = None,
        previous_rounds: list[DebateRound] | None = None,
        competitor_context: str = "",
    ) -> str:
        previous_rounds = previous_rounds or []
        attack_points = attack_points or []
        if not self._llm:
            risks = attack_points[:2] or evidence[:2] or ["valuation and industry risks"]
            return f"[Bear] {company_name} faces material risks: {'; '.join(risks)}."

        prompt = f"""You are a Bear researcher arguing AGAINST investing in {company_name} ({industry}).
Evidence:
{chr(10).join(evidence)}
Key attack angles:
{chr(10).join(attack_points)}
{f'Competitor context: {competitor_context}' if competitor_context else ''}
{f'Bull last said: {previous_rounds[-1].bull_argument}' if previous_rounds else ''}

Make a compelling bear argument in 2-3 sentences. Focus on risks and counter-evidence. Write in Chinese."""
        try:
            return str(self._llm.call("debate_bear", prompt))
        except Exception as exc:
            logger.warning("Bear LLM failed: %s", exc)
            return f"[Bear] {company_name} may be exposed to saturation, policy, and valuation risks."
