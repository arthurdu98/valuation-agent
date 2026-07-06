"""API request/response models (distinct from domain schemas in src/schemas.py)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.schemas import Market


# --- Companies ---


class CompanyCreate(BaseModel):
    ticker: str
    name: str
    market: Market
    industry: str
    competitors: list[str] = Field(default_factory=list)


class CompetitorsUpdate(BaseModel):
    competitors: list[str]


class DeleteResult(BaseModel):
    success: bool


# --- Compare ---


class ComparisonRow(BaseModel):
    ticker: str
    name: str
    industry: str
    market: str
    pe: float | None = None
    pb: float | None = None
    ps: float | None = None
    gross_margin: float | None = None
    roe: float | None = None
    revenue_growth: float | None = None
    net_margin: float | None = None
    market_cap_bn: float | None = None


class CompareResponse(BaseModel):
    rows: list[ComparisonRow]


# --- Runs ---


class RunCreate(BaseModel):
    ticker: str
    use_mock: bool = True
    debate_rounds: int = Field(default=2, ge=1, le=5)


class RunCreated(BaseModel):
    run_id: str
    status: str


class RunStatusResponse(BaseModel):
    run_id: str
    ticker: str
    company_name: str
    status: str
    created_at: str
    error: str | None = None
    result_available: bool = False


class RunSummary(BaseModel):
    run_id: str
    ticker: str
    company_name: str
    status: str
    created_at: str


class ResumeRequest(BaseModel):
    feedback: str


# --- Metrics ---


class MetricSubmit(BaseModel):
    ticker: str
    industry: str
    record_date: str | None = None
    values: dict[str, float]


class MetricSubmitResult(BaseModel):
    saved: int
    records: list[dict[str, Any]]
