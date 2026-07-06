from src.backend.schemas import Signal
from src.backend.agents.llm.router import LLMRouter
import logging

logger = logging.getLogger(__name__)

class RiskAssessment:
    def __init__(self, risk_level: str = "medium", risks: list[str] = None,
                 falsification_result: str = "", confidence_adjustment: float = 0):
        self.risk_level = risk_level  # low/medium/high/critical
        self.risks = risks or []
        self.falsification_result = falsification_result
        self.confidence_adjustment = confidence_adjustment  # negative = reduce confidence

class RiskFalsifier:
    """L4 Risk/Falsification agent. Adversarially challenges the debate conclusion."""

    def __init__(self, llm_router: LLMRouter | None = None):
        self._llm = llm_router

    def assess(
        self,
        ticker: str,
        company_name: str,
        industry: str,
        debate_conclusion: Signal,
        debate_confidence: float,
        bull_arguments: list[str],
        bear_arguments: list[str],
        pe_quantile: float | None = None,
        industry_risks: list[str] | None = None,
    ) -> RiskAssessment:
        """Adversarially challenge the debate conclusion."""

        # Rule-based risk checks
        risks = []
        confidence_adj = 0.0

        # Check valuation risk
        if pe_quantile is not None:
            if pe_quantile > 0.9 and debate_conclusion == Signal.BULLISH:
                risks.append("估值极高（PE分位>90%），看多结论需额外审慎")
                confidence_adj -= 15
            elif pe_quantile < 0.1 and debate_conclusion == Signal.BEARISH:
                risks.append("估值极低（PE分位<10%），看空结论可能忽略安全边际")
                confidence_adj -= 10

        # Add industry-specific risks
        if industry_risks:
            risks.extend(industry_risks[:3])

        # Determine risk level
        if abs(confidence_adj) >= 20:
            risk_level = "critical"
        elif abs(confidence_adj) >= 10:
            risk_level = "high"
        elif risks:
            risk_level = "medium"
        else:
            risk_level = "low"

        # LLM falsification attempt
        falsification = ""
        if self._llm:
            falsification = self._attempt_falsification(
                company_name, industry, debate_conclusion, bull_arguments, bear_arguments
            )

        return RiskAssessment(
            risk_level=risk_level,
            risks=risks,
            falsification_result=falsification,
            confidence_adjustment=confidence_adj,
        )

    def _attempt_falsification(self, company, industry, conclusion, bulls, bears) -> str:
        prompt = f"""You are a risk analyst tasked with FALSIFYING the investment conclusion for {company} ({industry}).

The debate concluded: {conclusion.value}

Bull arguments: {bulls[:3]}
Bear arguments: {bears[:3]}

Your job: Try to PROVE THIS CONCLUSION WRONG. What critical risks, blind spots, or logical fallacies could invalidate this conclusion? Consider:
- Policy/regulatory black swans
- Valuation bubble risk
- Industry cycle position
- Hidden leverage or accounting quality issues
- Competitive disruption threats

Write 2-3 key falsification arguments in Chinese. Be adversarial."""

        try:
            return self._llm.call("risk_falsify", prompt)
        except Exception as e:
            logger.warning(f"Falsification LLM failed: {e}")
            return "风控证伪模块暂时不可用。"
