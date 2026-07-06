"""Valuation run endpoints: start a run, stream SSE progress, fetch result."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from src.backend.api.deps import get_company_manager, get_run_registry
from src.backend.api.progress import ProgressEmitter
from src.backend.api.run_registry import RunRegistry
from src.backend.api.schemas_api import (
    ResumeRequest,
    RunCreate,
    RunCreated,
    RunStatusResponse,
    RunSummary,
)
from src.backend.api.static_data import MOCK_FINANCIALS
from src.backend.data.company_manager import CompanyManager
from src.backend.schemas import Market

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _build_state(company, use_mock: bool) -> dict:
    """Construct the pipeline input state (mirrors company_detail.py)."""
    financial_data: list[dict] = []
    if use_mock:
        for f in MOCK_FINANCIALS:
            financial_data.append({
                "ticker": company.ticker,
                "period": date.fromisoformat(f["period"]),
                "market": Market.A_SHARE,
                "revenue": Decimal(f["revenue"]),
                "net_profit": Decimal(f["net_profit"]),
                "gross_margin": f["gross_margin"],
                "roe": f["roe"],
                "total_assets": Decimal(f["total_assets"]),
                "total_liabilities": Decimal(f["total_liabilities"]),
                "operating_cashflow": Decimal(f["operating_cashflow"]),
                "eps": Decimal(f["eps"]),
                "bvps": Decimal(f["bvps"]),
            })
    return {
        "company": {"name": company.name},
        "ticker": company.ticker,
        "industry": company.industry,
        "competitors": company.competitors,
        "financial_data": financial_data,
        "industry_metrics": {"price_spread": 350, "batch_price": 2100} if use_mock else {},
    }


@router.post("", response_model=RunCreated, status_code=status.HTTP_202_ACCEPTED)
async def start_run(
    payload: RunCreate,
    cm: CompanyManager = Depends(get_company_manager),
    registry: RunRegistry = Depends(get_run_registry),
) -> RunCreated:
    company = next((c for c in cm.get_tracked_companies() if c.ticker == payload.ticker), None)
    if company is None:
        raise HTTPException(status_code=404, detail=f"未追踪的公司: {payload.ticker}")

    run_id = uuid.uuid4().hex
    record = registry.create(run_id, company.ticker, company.name)

    state = _build_state(company, payload.use_mock)
    loop = asyncio.get_running_loop()
    emitter = ProgressEmitter(loop, record.queue)

    def _emit_and_record(event: dict) -> None:
        # Forward to the live queue AND persist to the replay buffer.
        registry.record_event(run_id, event)
        emitter(event)

    def _work() -> None:
        # Runs in a thread-pool worker. Import here to defer heavy imports.
        from src.backend.agents.llm.router import LLMRouter
        from src.backend.graph.pipeline import ValuationPipeline
        from src.backend.graph.state import RunConfig

        record.status = "running"
        try:
            router_obj = LLMRouter("configs/llm.yaml")
            cfg = RunConfig(debate_rounds=payload.debate_rounds, require_human_approval=False)
            pipeline = ValuationPipeline(llm_router=router_obj, run_config=cfg)
            result = pipeline.run_sequential(state, progress_cb=_emit_and_record)
            record.result = result
            record.status = "error" if result.get("error") else "done"
            if result.get("error"):
                record.error = result["error"]
        except Exception as e:  # noqa: BLE001
            record.status = "error"
            record.error = str(e)
            _emit_and_record({"stage": "error", "status": "error", "message": str(e)})
        finally:
            # Terminal sentinel so the SSE generator can close.
            _emit_and_record({
                "stage": "done",
                "status": record.status,
                "result_available": record.result is not None,
            })

    loop.run_in_executor(None, _work)
    return RunCreated(run_id=run_id, status="pending")


@router.get("/{run_id}/stream")
async def stream_run(
    run_id: str,
    registry: RunRegistry = Depends(get_run_registry),
):
    record = registry.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run 不存在")

    async def event_generator():
        # Replay any events already buffered (late subscriber catch-up).
        replayed = 0
        for event in list(record.events):
            replayed += 1
            yield _format(event)
            if event.get("stage") == "done":
                return

        while True:
            try:
                event = await asyncio.wait_for(record.queue.get(), timeout=15.0)
            except asyncio.TimeoutError:
                # Heartbeat comment to keep the connection alive during LLM waits.
                yield {"event": "ping", "data": ""}
                continue
            # Skip events we already replayed from the buffer.
            if replayed > 0:
                replayed -= 1
                continue
            yield _format(event)
            if event.get("stage") == "done":
                return

    return EventSourceResponse(event_generator())


def _format(event: dict) -> dict:
    """Map a progress event to an SSE frame (event name + JSON data)."""
    stage = event.get("stage")
    if stage == "done":
        name = "done"
    elif stage == "error" or event.get("status") == "error":
        name = "error"
    else:
        name = "progress"
    return {"event": name, "data": json.dumps(event, ensure_ascii=False)}


@router.get("", response_model=list[RunSummary])
def list_runs(registry: RunRegistry = Depends(get_run_registry)) -> list[RunSummary]:
    return [
        RunSummary(
            run_id=r.run_id,
            ticker=r.ticker,
            company_name=r.company_name,
            status=r.status,
            created_at=r.created_at,
        )
        for r in registry.all()
    ]


@router.get("/{run_id}", response_model=RunStatusResponse)
def run_status(
    run_id: str,
    registry: RunRegistry = Depends(get_run_registry),
) -> RunStatusResponse:
    record = registry.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run 不存在")
    return RunStatusResponse(
        run_id=record.run_id,
        ticker=record.ticker,
        company_name=record.company_name,
        status=record.status,
        created_at=record.created_at,
        error=record.error,
        result_available=record.result is not None,
    )


@router.get("/{run_id}/result")
def run_result(
    run_id: str,
    registry: RunRegistry = Depends(get_run_registry),
) -> dict:
    record = registry.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run 不存在")
    if record.result is None:
        raise HTTPException(status_code=409, detail="run 尚未完成")
    return record.result


@router.post("/{run_id}/resume", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def resume_run(run_id: str, payload: ResumeRequest) -> dict:
    """Human-in-the-loop resume — deferred (see plan: InMemorySaver constraint)."""
    raise HTTPException(
        status_code=501,
        detail="人工复核续跑尚未实现（MVP 使用无中断的 run_sequential）",
    )
