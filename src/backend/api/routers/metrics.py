"""Industry metric submission endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.backend.api.deps import get_industry_plugin
from src.backend.api.schemas_api import MetricSubmit, MetricSubmitResult

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.post("", response_model=MetricSubmitResult)
def submit_metrics(payload: MetricSubmit) -> MetricSubmitResult:
    """Submit industry metric values for a company.

    MVP: validates metric names against the plugin, echoes back saved non-zero
    values. Does NOT persist to the database (mirrors current Streamlit behavior).
    """
    plugin = get_industry_plugin(payload.industry)
    if plugin is None:
        raise HTTPException(status_code=404, detail=f"行业 '{payload.industry}' 无插件")

    valid_names = {m.name for m in plugin.metrics}
    records = []
    for name, value in payload.values.items():
        if name not in valid_names:
            continue
        if value == 0:
            continue
        records.append({
            "ticker": payload.ticker,
            "metric_name": name,
            "metric_value": value,
            "recorded_at": payload.record_date or datetime.now(timezone.utc).isoformat(),
            "source": "manual_input",
            "confidence": 1.0,
        })

    return MetricSubmitResult(saved=len(records), records=records)


@router.get("/{ticker}")
def get_metrics(ticker: str, metric: str | None = None, limit: int = 50) -> list[dict]:
    """Retrieve historical metric records for a company.

    MVP: DB is not wired, so always returns empty. Once the DB persistence layer
    is activated, this will query IndustryMetricModel.
    """
    # TODO: wire to DB session when persistence is activated.
    return []
