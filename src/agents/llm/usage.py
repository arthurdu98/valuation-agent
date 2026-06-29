"""LLM usage tracking and cost aggregation."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class UsageRecord:
    model: str
    role: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    estimated_cost: float = 0.0
    timestamp: float = 0.0


class UsageTracker:
    """Tracks LLM calls by model and role."""

    def __init__(self) -> None:
        self._records: list[UsageRecord] = []

    def record(
        self,
        model: str,
        role: str,
        prompt: str,
        response: str,
        latency_ms: float,
        input_cost_per_1k: float,
        output_cost_per_1k: float,
    ) -> UsageRecord:
        input_tokens = max(len(prompt) // 4, 1)
        output_tokens = max(len(response) // 4, 1)
        estimated_cost = (
            input_tokens * input_cost_per_1k + output_tokens * output_cost_per_1k
        ) / 1000
        record = UsageRecord(
            model=model,
            role=role,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            estimated_cost=estimated_cost,
            timestamp=time.time(),
        )
        self._records.append(record)
        return record

    @property
    def records(self) -> list[UsageRecord]:
        return list(self._records)

    def get_usage_stats(self) -> dict:
        if not self._records:
            return {"total_calls": 0, "total_cost": 0, "by_model": {}, "by_role": {}}

        by_model: dict[str, dict] = {}
        by_role: dict[str, dict] = {}
        for record in self._records:
            by_model.setdefault(record.model, {"calls": 0, "cost": 0.0, "tokens": 0})
            by_model[record.model]["calls"] += 1
            by_model[record.model]["cost"] += record.estimated_cost
            by_model[record.model]["tokens"] += record.input_tokens + record.output_tokens

            by_role.setdefault(record.role, {"calls": 0, "cost": 0.0})
            by_role[record.role]["calls"] += 1
            by_role[record.role]["cost"] += record.estimated_cost

        return {
            "total_calls": len(self._records),
            "total_cost": sum(record.estimated_cost for record in self._records),
            "by_model": by_model,
            "by_role": by_role,
        }
