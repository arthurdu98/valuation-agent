import logging
import uuid
from datetime import datetime
from dataclasses import dataclass, field
import json
from pathlib import Path
from src.backend.schemas import Signal
from src.backend.agents.llm.router import LLMRouter

logger = logging.getLogger(__name__)

@dataclass
class Reflection:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str = ""
    ticker: str = ""
    industry: str = ""
    predicted_signal: Signal = Signal.NEUTRAL
    actual_outcome: str = ""
    correct_arguments: list[str] = field(default_factory=list)
    failed_arguments: list[str] = field(default_factory=list)
    lesson_learned: str = ""
    created_at: datetime = field(default_factory=datetime.now)

class ReflectionMemory:
    """Stores and retrieves historical decision reflections for learning."""

    def __init__(self, llm_router: LLMRouter | None = None, storage_path: str | Path = "data/reflections.jsonl"):
        self._llm = llm_router
        self._storage_path = Path(storage_path)
        self._reflections: list[Reflection] = []
        self._load()
        logger.info("ReflectionMemory initialized")

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        for line in self._storage_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            raw["predicted_signal"] = Signal(raw.get("predicted_signal", Signal.NEUTRAL.value))
            raw["created_at"] = datetime.fromisoformat(raw["created_at"])
            self._reflections.append(Reflection(**raw))

    def _persist(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for reflection in self._reflections:
            raw = reflection.__dict__.copy()
            raw["predicted_signal"] = reflection.predicted_signal.value
            raw["created_at"] = reflection.created_at.isoformat()
            lines.append(json.dumps(raw, ensure_ascii=False))
        self._storage_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    def record_decision(self, decision_id: str, ticker: str, industry: str,
                       predicted_signal: Signal, key_arguments: list[str]) -> None:
        """Record a confirmed decision for future reflection."""
        reflection = Reflection(
            decision_id=decision_id,
            ticker=ticker,
            industry=industry,
            predicted_signal=predicted_signal,
        )
        self._reflections.append(reflection)
        self._persist()
        logger.info(f"Decision recorded: {ticker} -> {predicted_signal.value}")

    def generate_reflection(
        self,
        decision_id: str,
        actual_outcome: str,
        actual_price_change: float | None = None,
    ) -> Reflection | None:
        """Compare prediction vs actual, generate reflection."""
        # Find the decision
        decision = next((r for r in self._reflections if r.decision_id == decision_id), None)
        if not decision:
            logger.warning(f"Decision {decision_id} not found")
            return None

        decision.actual_outcome = actual_outcome

        # Generate lesson using LLM
        if self._llm:
            prompt = f"""Reflect on this investment decision:
Company: {decision.ticker} ({decision.industry})
Prediction: {decision.predicted_signal.value}
Actual outcome: {actual_outcome}
{f'Price change: {actual_price_change:.1%}' if actual_price_change else ''}

What went right? What went wrong? What's the key lesson for future decisions about this company or industry?
Write a concise reflection in Chinese (2-3 sentences)."""
            try:
                decision.lesson_learned = str(self._llm.call("reflection", prompt))
            except Exception as e:
                logger.warning(f"Reflection LLM failed: {e}")
                decision.lesson_learned = f"预测: {decision.predicted_signal.value}, 实际: {actual_outcome}"
        else:
            decision.lesson_learned = f"预测: {decision.predicted_signal.value}, 实际: {actual_outcome}"

        self._persist()
        return decision

    def retrieve_relevant(
        self,
        company: str | None = None,
        industry: str | None = None,
        limit: int = 5,
    ) -> list[Reflection]:
        """Retrieve relevant historical reflections.

        Searches by company first, then by industry for cross-company transfer.
        """
        scored: list[tuple[int, Reflection]] = []

        for reflection in self._reflections:
            if not reflection.lesson_learned:
                continue
            score = 0
            if company and reflection.ticker == company:
                score += 3
            if industry and reflection.industry == industry:
                score += 2
            if score:
                scored.append((score, reflection))
        scored.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
        return [reflection for _, reflection in scored[:limit]]

    def get_lessons_for_debate(self, ticker: str, industry: str) -> list[str]:
        """Get relevant lessons to inject into debate context."""
        reflections = self.retrieve_relevant(company=ticker, industry=industry)
        return [r.lesson_learned for r in reflections if r.lesson_learned]
