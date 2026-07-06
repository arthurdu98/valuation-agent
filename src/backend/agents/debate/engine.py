from dataclasses import dataclass, field
from src.backend.schemas import DebateRound, DebateResult, Signal
from src.backend.agents.llm.router import LLMRouter
from src.backend.agents.debate.bear import BearResearcher
from src.backend.agents.debate.bull import BullResearcher
from src.backend.agents.debate.judge import DebateJudge
import logging

logger = logging.getLogger(__name__)


class DebateEngine:
    """Orchestrates Bull/Bear multi-round debate with judge arbitration."""

    def __init__(self, llm_router: LLMRouter | None = None, max_rounds: int = 3):
        self._llm = llm_router
        self.max_rounds = max_rounds
        self._bull = BullResearcher(llm_router)
        self._bear = BearResearcher(llm_router)
        self._judge = DebateJudge(llm_router)

    def run_debate(
        self,
        company_name: str,
        ticker: str,
        industry: str,
        bull_evidence: list[str],
        bear_evidence: list[str],
        bear_attack_points: list[str] = None,
        competitor_context: str = "",
        progress_cb=None,
    ) -> DebateResult:
        emit = progress_cb or (lambda event: None)
        rounds = []
        for round_num in range(1, self.max_rounds + 1):
            emit({
                "stage": "l3",
                "status": "progress",
                "detail": f"第 {round_num} 轮",
                "round": round_num,
                "total": self.max_rounds,
            })
            bull_arg = self._bull.argue(
                company_name, industry, bull_evidence, rounds, competitor_context
            )
            bear_arg = self._bear.argue(
                company_name,
                industry,
                bear_evidence,
                bear_attack_points,
                rounds,
                competitor_context,
            )
            rounds.append(DebateRound(round_num=round_num, bull_argument=bull_arg, bear_argument=bear_arg))

        judge_summary, stance, confidence = self._judge.judge(company_name, rounds)

        return DebateResult(
            rounds=rounds,
            judge_summary=judge_summary,
            final_stance=stance,
            confidence=confidence,
            key_contentions=[r.bear_argument[:100] for r in rounds],
        )

    def _generate_bull_argument(self, company, industry, evidence, prev_rounds, competitor_ctx) -> str:
        if not self._llm:
            return f"[Bull] Based on evidence, {company} shows strong fundamentals in {industry}."
        prompt = f"""You are a Bull researcher arguing FOR investing in {company} ({industry}).
Evidence: {evidence}
{f'Competitor context: {competitor_ctx}' if competitor_ctx else ''}
Previous rounds: {len(prev_rounds)}
{f'Bear last said: {prev_rounds[-1].bear_argument}' if prev_rounds else ''}
Make a compelling bull argument in 2-3 sentences. Cite specific data. Write in Chinese."""
        try:
            return self._llm.call("debate_bull", prompt)
        except Exception as e:
            logger.warning(f"Bull LLM failed: {e}")
            return f"[Bull] {company} demonstrates strong competitive positioning in {industry}."

    def _generate_bear_argument(self, company, industry, evidence, attack_points, prev_rounds, competitor_ctx) -> str:
        if not self._llm:
            return f"[Bear] Despite appearances, {company} faces risks in {industry}."
        attacks = "\n".join(attack_points or [])
        prompt = f"""You are a Bear researcher arguing AGAINST investing in {company} ({industry}).
Evidence: {evidence}
Key attack angles: {attacks}
{f'Competitor context: {competitor_ctx}' if competitor_ctx else ''}
{f'Bull last said: {prev_rounds[-1].bull_argument}' if prev_rounds else ''}
Make a compelling bear argument in 2-3 sentences. Focus on risks and counter-evidence. Write in Chinese."""
        try:
            return self._llm.call("debate_bear", prompt)
        except Exception as e:
            logger.warning(f"Bear LLM failed: {e}")
            return f"[Bear] Key risks for {company}: market saturation, regulatory pressure."

    def _judge_debate(self, company, rounds: list[DebateRound]) -> tuple[str, Signal, float]:
        if not self._llm:
            return "Debate concluded without LLM judge.", Signal.NEUTRAL, 50.0

        debate_text = ""
        for r in rounds:
            debate_text += f"Round {r.round_num}:\nBull: {r.bull_argument}\nBear: {r.bear_argument}\n\n"

        prompt = f"""You are the Research Manager judging a bull/bear debate on {company}.

{debate_text}

Judge the debate:
1. Which side had stronger evidence?
2. What are the key unresolved contentions?
3. Your final stance: bullish, bearish, or neutral?
4. Confidence (0-100)?

Format: Start with your stance (bullish/bearish/neutral) and confidence on line 1 as "STANCE:confidence", then your analysis. Write in Chinese."""

        try:
            response = self._llm.call("debate_judge", prompt)
            # Parse stance from response
            first_line = response.strip().split("\n")[0]
            if "bullish" in first_line.lower():
                stance = Signal.BULLISH
            elif "bearish" in first_line.lower():
                stance = Signal.BEARISH
            else:
                stance = Signal.NEUTRAL
            # Try to parse confidence
            confidence = 50.0
            if ":" in first_line:
                try:
                    confidence = float(first_line.split(":")[1].strip())
                except (ValueError, IndexError):
                    pass
            return response, stance, confidence
        except Exception as e:
            logger.warning(f"Judge LLM failed: {e}")
            return "Judge unavailable.", Signal.NEUTRAL, 50.0
