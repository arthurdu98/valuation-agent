"""Debate judge agent."""

from __future__ import annotations

import logging

from src.agents.llm.router import LLMRouter
from src.schemas import DebateRound, Signal

logger = logging.getLogger(__name__)


class DebateJudge:
    """Arbitrates bull/bear debates and returns a stance."""

    def __init__(self, llm_router: LLMRouter | None = None) -> None:
        self._llm = llm_router

    def judge(self, company_name: str, rounds: list[DebateRound]) -> tuple[str, Signal, float]:
        if not self._llm:
            return "Debate concluded without LLM judge.", Signal.NEUTRAL, 50.0

        debate_text = "\n".join(
            f"Round {round_.round_num}:\nBull: {round_.bull_argument}\nBear: {round_.bear_argument}"
            for round_ in rounds
        )
        prompt = f"""You are the Research Manager judging a bull/bear debate on {company_name}.

{debate_text}

Judge the debate:
1. Which side had stronger evidence?
2. What are the key unresolved contentions?
3. Your final stance: bullish, bearish, or neutral?
4. Confidence (0-100)?

Format: Start with your stance and confidence on line 1 as "STANCE:confidence". Write in Chinese."""
        try:
            response = str(self._llm.call("debate_judge", prompt))
            first_line = response.strip().split("\n")[0]
            stance = Signal.NEUTRAL
            if "bullish" in first_line.lower():
                stance = Signal.BULLISH
            elif "bearish" in first_line.lower():
                stance = Signal.BEARISH

            confidence = 50.0
            if ":" in first_line:
                try:
                    confidence = float(first_line.split(":", 1)[1].strip())
                except ValueError:
                    confidence = 50.0
            return response, stance, confidence
        except Exception as exc:
            logger.warning("Judge LLM failed: %s", exc)
            return "Judge unavailable.", Signal.NEUTRAL, 50.0
