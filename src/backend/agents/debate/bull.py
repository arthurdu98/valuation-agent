"""Bull-side debate researcher agent."""

from __future__ import annotations

import logging

from src.backend.agents.llm.router import LLMRouter
from src.backend.schemas import DebateRound

logger = logging.getLogger(__name__)


class BullResearcher:
    """Builds pro-investment arguments from positive evidence."""

    def __init__(self, llm_router: LLMRouter | None = None) -> None:
        self._llm = llm_router

    def argue(
        self,
        company_name: str,
        industry: str,
        evidence: list[str],
        previous_rounds: list[DebateRound] | None = None,
        competitor_context: str = "",
    ) -> str:
        previous_rounds = previous_rounds or []
        if not self._llm:
            return (
                f"[Bull] {company_name} has positive evidence in {industry}: "
                f"{'; '.join(evidence[:2]) or 'fundamentals remain constructive'}."
            )

        prompt = f"""You are a Bull researcher arguing FOR investing in {company_name} ({industry}).
Evidence:
{chr(10).join(evidence)}
{f'Competitor context: {competitor_context}' if competitor_context else ''}
{f'Bear last said: {previous_rounds[-1].bear_argument}' if previous_rounds else ''}

Make a compelling bull argument in 2-3 sentences. Cite specific data. Write in Chinese."""
        try:
            return str(self._llm.call("debate_bull", prompt))
        except Exception as exc:
            logger.warning("Bull LLM failed: %s", exc)
            return f"[Bull] {company_name} demonstrates resilient fundamentals and competitive positioning."
