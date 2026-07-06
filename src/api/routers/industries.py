"""Industry plugin + comparison endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import (
    available_industries,
    get_company_manager,
    get_industry_plugin,
)
from src.api.schemas_api import ComparisonRow, CompareResponse
from src.api.static_data import STATIC_METRICS
from src.data.company_manager import CompanyManager
from src.schemas import AlertRule, MetricDefinition

router = APIRouter(prefix="/api/industries", tags=["industries"])


@router.get("", response_model=list[str])
def list_industries(cm: CompanyManager = Depends(get_company_manager)) -> list[str]:
    """Industries present among tracked companies."""
    return sorted({c.industry for c in cm.get_tracked_companies()})


@router.get("/{industry}/metrics", response_model=list[MetricDefinition])
def industry_metrics(industry: str) -> list[MetricDefinition]:
    plugin = get_industry_plugin(industry)
    if plugin is None:
        raise HTTPException(
            status_code=404,
            detail=f"行业 '{industry}' 无插件（可用: {available_industries()}）",
        )
    return plugin.metrics


@router.get("/{industry}/alert-rules", response_model=list[AlertRule])
def industry_alert_rules(industry: str) -> list[AlertRule]:
    plugin = get_industry_plugin(industry)
    if plugin is None:
        raise HTTPException(status_code=404, detail=f"行业 '{industry}' 无插件")
    return plugin.get_alert_rules()


@router.get("/{industry}/bear-points", response_model=list[str])
def industry_bear_points(industry: str) -> list[str]:
    plugin = get_industry_plugin(industry)
    if plugin is None:
        raise HTTPException(status_code=404, detail=f"行业 '{industry}' 无插件")
    return plugin.get_bear_attack_points()


# Comparison endpoint lives here (industry-scoped filter over tracked companies).
compare_router = APIRouter(prefix="/api", tags=["compare"])


@compare_router.get("/compare", response_model=CompareResponse)
def compare(
    industry: str = Query(default="全部"),
    cm: CompanyManager = Depends(get_company_manager),
) -> CompareResponse:
    companies = cm.get_tracked_companies()
    if industry and industry != "全部":
        companies = [c for c in companies if c.industry == industry]

    rows: list[ComparisonRow] = []
    for c in companies:
        m = STATIC_METRICS.get(c.ticker, {})
        rows.append(
            ComparisonRow(
                ticker=c.ticker,
                name=c.name,
                industry=c.industry,
                market=c.market.value.upper(),
                pe=m.get("pe"),
                pb=m.get("pb"),
                ps=m.get("ps"),
                gross_margin=m.get("gross_margin"),
                roe=m.get("roe"),
                revenue_growth=m.get("revenue_growth"),
                net_margin=m.get("net_margin"),
                market_cap_bn=m.get("market_cap_bn"),
            )
        )
    return CompareResponse(rows=rows)
