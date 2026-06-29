from src.schemas import ValuationReport, Signal, MasterSignal, DebateResult
from src.agents.llm.router import LLMRouter
from src.agents.risk.falsifier import RiskAssessment
from decimal import Decimal
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

class FinalEstimator:
    """L5 Final Valuation agent. Synthesizes all prior layers into a final report."""

    def __init__(self, llm_router: LLMRouter | None = None):
        self._llm = llm_router

    def estimate(
        self,
        ticker: str,
        company_name: str,
        industry: str,
        master_signals: list[MasterSignal],
        debate_result: DebateResult,
        risk_assessment: RiskAssessment,
        pe_quantile: float | None = None,
        dcf_value: float | None = None,
        monte_carlo_percentiles: dict | None = None,
        competitor_comparison: dict | None = None,
    ) -> ValuationReport:
        """Generate final valuation report."""

        # Aggregate master signals
        bullish_count = sum(1 for s in master_signals if s.signal == Signal.BULLISH)
        bearish_count = sum(1 for s in master_signals if s.signal == Signal.BEARISH)
        avg_confidence = sum(s.confidence for s in master_signals) / max(len(master_signals), 1)

        # Determine valuation range
        if monte_carlo_percentiles:
            val_low = Decimal(str(monte_carlo_percentiles.get("p25", 0)))
            val_mid = Decimal(str(monte_carlo_percentiles.get("p50", 0)))
            val_high = Decimal(str(monte_carlo_percentiles.get("p75", 0)))
        elif dcf_value:
            val_mid = Decimal(str(dcf_value))
            val_low = val_mid * Decimal("0.8")
            val_high = val_mid * Decimal("1.2")
        else:
            val_low = Decimal("0")
            val_mid = Decimal("0")
            val_high = Decimal("0")

        # Collect bull/bear arguments
        bull_args = [s.reasoning[:200] for s in master_signals if s.signal == Signal.BULLISH][:5]
        bear_args = [s.reasoning[:200] for s in master_signals if s.signal == Signal.BEARISH][:5]
        if debate_result.final_stance == Signal.BULLISH:
            bull_args.insert(0, debate_result.judge_summary[:200])
        else:
            bear_args.insert(0, debate_result.judge_summary[:200])

        # Key assumptions
        assumptions = [
            f"Masters consensus: {bullish_count} bullish, {bearish_count} bearish",
            f"Debate conclusion: {debate_result.final_stance.value} (confidence: {debate_result.confidence:.0f}%)",
            f"Risk level: {risk_assessment.risk_level}",
        ]

        # Adjusted confidence
        final_confidence = avg_confidence + risk_assessment.confidence_adjustment
        final_confidence = max(0, min(100, final_confidence))

        # Generate LLM synthesis if available
        if self._llm:
            synthesis = self._generate_synthesis(
                company_name, industry, master_signals, debate_result, risk_assessment
            )
            if synthesis:
                bull_args.append(f"[综合判断] {synthesis[:300]}")

        return ValuationReport(
            id=uuid.uuid4(),
            ticker=ticker,
            valuation_low=val_low,
            valuation_mid=val_mid,
            valuation_high=val_high,
            pe_quantile=pe_quantile or 0.5,
            bull_arguments=bull_args,
            bear_arguments=bear_args,
            key_assumptions=assumptions,
            sensitivity_factors={"confidence_adjustment": risk_assessment.confidence_adjustment},
            competitor_comparison=competitor_comparison or {},
            human_approved=False,
            created_at=datetime.now(),
        )

    def _generate_synthesis(self, company, industry, signals, debate, risk) -> str:
        prompt = f"""You are the final portfolio analyst for {company} ({industry}).

Master signals: {[(s.signal.value, s.confidence) for s in signals]}
Debate conclusion: {debate.final_stance.value} (confidence {debate.confidence}%)
Risk assessment: {risk.risk_level} - {risk.risks[:3]}

Write a 2-sentence final synthesis in Chinese. Be decisive."""
        try:
            return self._llm.call("final_valuation", prompt)
        except Exception as e:
            logger.warning(f"Final synthesis LLM failed: {e}")
            return ""
