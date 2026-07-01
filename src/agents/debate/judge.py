"""Debate judge agent."""

from __future__ import annotations

import logging
import re

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
4. Confidence level (0-100)?

IMPORTANT: Your FIRST LINE must be exactly in this format (no other text on that line):
STANCE:bullish:75
or
STANCE:neutral:50
or
STANCE:bearish:60

Then write your full analysis in Chinese starting from line 2."""
        try:
            response = str(self._llm.call("debate_judge", prompt))
            first_line = response.strip().split("\n")[0].strip()

            # Parse "STANCE:bullish:75" format
            stance = Signal.NEUTRAL
            confidence = 50.0

            # Try structured format first: STANCE:<signal>:<confidence>
            m = re.match(r"STANCE:(\w+):(\d+(?:\.\d+)?)", first_line, re.IGNORECASE)
            if m:
                signal_str = m.group(1).lower()
                if signal_str == "bullish":
                    stance = Signal.BULLISH
                elif signal_str == "bearish":
                    stance = Signal.BEARISH
                else:
                    stance = Signal.NEUTRAL
                confidence = float(m.group(2))
            else:
                # Fallback: scan full first line for keywords
                fl_lower = first_line.lower()
                if "bullish" in fl_lower:
                    stance = Signal.BULLISH
                elif "bearish" in fl_lower:
                    stance = Signal.BEARISH
                # Try to pull any number as confidence
                nums = re.findall(r"\d+(?:\.\d+)?", first_line)
                if nums:
                    confidence = float(nums[-1])

            # Strip the STANCE header line from the summary shown to users
            lines = response.strip().split("\n")
            summary = "\n".join(lines[1:]).strip() if len(lines) > 1 else response

            return summary, stance, confidence
        except Exception as exc:
            logger.warning("Judge LLM failed: %s", exc)
            return "Judge unavailable.", Signal.NEUTRAL, 50.0
