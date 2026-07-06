"""LLM fallback execution helpers."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class LLMFallbackRunner:
    """Runs a callable across a primary model and configured fallback chain."""

    def __init__(self, fallback_chain: list[str]) -> None:
        self._fallback_chain = fallback_chain

    def models_for(self, primary_model: str) -> list[str]:
        return [primary_model] + [
            model for model in self._fallback_chain if model != primary_model
        ]

    def run(
        self,
        primary_model: str,
        invoke_model: Callable[[str], Any],
        *,
        role: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> tuple[str, Any, float]:
        """Try each model until one succeeds."""
        last_error: Exception | None = None
        for model_name in self.models_for(primary_model):
            for attempt in range(max_retries):
                try:
                    start = time.time()
                    response = invoke_model(model_name)
                    latency_ms = (time.time() - start) * 1000
                    return model_name, response, latency_ms
                except Exception as exc:
                    last_error = exc
                    logger.warning(
                        "[%s] %s attempt %s failed: %s",
                        role,
                        model_name,
                        attempt + 1,
                        exc,
                    )
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (2**attempt))
            logger.error("[%s] %s exhausted retries", role, model_name)
        raise RuntimeError(
            f"All models failed for role '{role}'. Last error: {last_error}"
        )
