"""Progress event emitter bridging the sync pipeline (worker thread) to asyncio.

The L1-L5 pipeline runs in a thread-pool worker (it is sync/blocking). Progress
events must be pushed onto an ``asyncio.Queue`` that lives on the event loop.
``asyncio.Queue`` is NOT thread-safe, so we schedule the put via
``loop.call_soon_threadsafe`` — this is the one correctness-critical bridge in
the whole SSE design.
"""

from __future__ import annotations

import asyncio
from typing import Any


class ProgressEmitter:
    """Thread-safe callable that forwards pipeline events to an asyncio queue.

    Instantiated on the event loop (so it can capture the running loop), then
    passed as ``progress_cb`` into ``pipeline.run_sequential`` which invokes it
    from a worker thread.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue[dict[str, Any]]):
        self._loop = loop
        self._queue = queue

    def __call__(self, event: dict[str, Any]) -> None:
        """Push an event onto the queue from any thread."""
        self._loop.call_soon_threadsafe(self._queue.put_nowait, event)


# Stage metadata: ordered list of pipeline stages with human labels and the
# cumulative progress percentage reached when each stage *completes*.
STAGES: list[dict[str, Any]] = [
    {"stage": "l1", "label": "L1 基础分析层", "pct_done": 20},
    {"stage": "l2", "label": "L2 投资大师层", "pct_done": 45},
    {"stage": "l3", "label": "L3 多空辩论层", "pct_done": 70},
    {"stage": "l4", "label": "L4 风险证伪层", "pct_done": 85},
    {"stage": "l5", "label": "L5 综合估值层", "pct_done": 100},
]
