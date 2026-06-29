from abc import ABC, abstractmethod
from src.schemas import MasterSignal, Signal, FinancialStatements
from src.agents.llm.router import LLMRouter
import logging

logger = logging.getLogger(__name__)


class CompanyAnalysisData:
    """Data bundle passed to master agents for analysis."""
    def __init__(
        self,
        ticker: str,
        name: str,
        industry: str,
        financials: list[FinancialStatements] | None = None,
        industry_metrics: dict[str, float] | None = None,
        competitor_data: dict | None = None,
        pe_quantile: float | None = None,
        graham_number: float | None = None,
        current_price: float | None = None,
    ):
        self.ticker = ticker
        self.name = name
        self.industry = industry
        self.financials = financials or []
        self.industry_metrics = industry_metrics or {}
        self.competitor_data = competitor_data or {}
        self.pe_quantile = pe_quantile
        self.graham_number = graham_number
        self.current_price = current_price

    @property
    def latest_financials(self) -> FinancialStatements | None:
        return self.financials[0] if self.financials else None


class MasterAgent(ABC):
    """Base class for investment master agents.

    Each master agent follows the two-stage pattern:
    1. score() - Deterministic Python scoring (hard-coded thresholds)
    2. narrate() - LLM narration in the master's voice
    """

    def __init__(self, llm_router: LLMRouter | None = None):
        self._llm = llm_router

    @property
    @abstractmethod
    def name(self) -> str:
        """Master's name (e.g., 'Warren Buffett')"""

    @property
    @abstractmethod
    def philosophy(self) -> str:
        """One-sentence summary of investment philosophy"""

    @property
    def llm_role(self) -> str:
        """LLM role for narration routing. Override if needed."""
        return "master_narrate"

    @abstractmethod
    def score(self, data: CompanyAnalysisData) -> dict:
        """Deterministic scoring. Returns dict of {criterion: score}.
        No LLM involved - pure Python logic with hard thresholds.
        Total score should be in range [-10, 10].
        """

    def _score_to_signal(self, total_score: float) -> Signal:
        """Convert numeric score to signal."""
        if total_score >= 3:
            return Signal.BULLISH
        elif total_score <= -3:
            return Signal.BEARISH
        return Signal.NEUTRAL

    def _score_to_confidence(self, total_score: float) -> float:
        """Convert score magnitude to confidence (0-100)."""
        return min(abs(total_score) * 10, 100.0)

    def narrate(self, data: CompanyAnalysisData, scoring_result: dict) -> MasterSignal:
        """Generate narration in the master's voice using LLM."""
        total_score = sum(scoring_result.values())
        signal = self._score_to_signal(total_score)
        confidence = self._score_to_confidence(total_score)

        # If no LLM available, return without narration
        if not self._llm:
            reasoning = f"[{self.name}] Score: {total_score:.1f}. Criteria: {scoring_result}"
            return MasterSignal(signal=signal, confidence=confidence, reasoning=reasoning)

        prompt = self._build_narration_prompt(data, scoring_result, signal, confidence)
        try:
            reasoning = self._llm.call(self.llm_role, prompt)
        except Exception as e:
            logger.warning(f"{self.name} narration failed: {e}")
            reasoning = f"[{self.name}] Score: {total_score:.1f}. Details: {scoring_result}"

        return MasterSignal(signal=signal, confidence=confidence, reasoning=reasoning)

    def _build_narration_prompt(self, data: CompanyAnalysisData, scores: dict, signal: Signal, confidence: float) -> str:
        """Build the narration prompt. Override for custom prompts."""
        return f"""You are {self.name}. Your investment philosophy: {self.philosophy}

Analyze {data.name} ({data.ticker}) in the {data.industry} industry.

Your scoring system produced these results:
{scores}

Overall signal: {signal.value} (confidence: {confidence:.0f}%)

Write a 2-3 paragraph analysis in {self.name}'s voice and style, explaining why you gave this rating. Reference specific financial metrics. Be concise and insightful. Write in Chinese."""

    def analyze(self, data: CompanyAnalysisData) -> MasterSignal:
        """Full analysis: score then narrate."""
        scores = self.score(data)
        return self.narrate(data, scores)
