"""In-memory registry of valuation runs.

Holds each run's status, live progress queue, replay buffer, and final result.
This is process-local state — the API MUST run with a single Uvicorn worker.
Multi-worker deployments require moving this to Redis/Postgres.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

RunStatus = Literal["pending", "running", "done", "error"]


@dataclass
class RunRecord:
    """State for a single valuation run."""

    run_id: str
    ticker: str
    company_name: str
    status: RunStatus = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)
    events: list[dict[str, Any]] = field(default_factory=list)  # replay buffer
    result: dict[str, Any] | None = None
    error: str | None = None


class RunRegistry:
    """Process-local store of runs keyed by run_id."""

    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}

    def create(self, run_id: str, ticker: str, company_name: str) -> RunRecord:
        record = RunRecord(run_id=run_id, ticker=ticker, company_name=company_name)
        self._runs[run_id] = record
        return record

    def get(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    def all(self) -> list[RunRecord]:
        return list(self._runs.values())

    def record_event(self, run_id: str, event: dict[str, Any]) -> None:
        """Append an event to the replay buffer (for late SSE subscribers)."""
        record = self._runs.get(run_id)
        if record is not None:
            record.events.append(event)


# Module-level singleton — shared across all requests in the single worker.
registry = RunRegistry()
