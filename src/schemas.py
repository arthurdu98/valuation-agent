"""Core Pydantic schemas for the valuation system."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# --- Enums ---


class Market(str, Enum):
    """Supported market types."""

    A_SHARE = "a_share"
    HK = "hk"
    US = "us"


class Signal(str, Enum):
    """Trading signal types."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class CollectionMode(str, Enum):
    """Data collection mode."""

    AUTO = "auto"
    SEMI_AUTO = "semi_auto"
    MANUAL = "manual"


# --- Core Models ---


class Company(BaseModel):
    """Company information model."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    ticker: str
    name: str
    market: Market
    industry: str
    competitors: list[str] = Field(default_factory=list)
    custom_groups: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: Optional[datetime] = None


class FinancialStatements(BaseModel):
    """Financial statements data model."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    ticker: str
    period: date
    market: Market
    revenue: Decimal
    net_profit: Decimal
    gross_margin: float
    roe: float
    contract_liabilities: Optional[Decimal] = None
    total_assets: Decimal
    total_liabilities: Decimal
    operating_cashflow: Decimal
    eps: Decimal
    bvps: Decimal
    raw_data: dict = Field(default_factory=dict)
    fetched_at: Optional[datetime] = None


class IndustryMetricRecord(BaseModel):
    """Industry metric record model."""

    model_config = ConfigDict(from_attributes=True)

    ticker: str
    metric_name: str
    metric_value: float
    recorded_at: datetime
    source: str
    confidence: float = 1.0


class MasterSignal(BaseModel):
    """Master trading signal model."""

    model_config = ConfigDict(from_attributes=True)

    signal: Signal
    confidence: float = Field(ge=0, le=100)
    reasoning: str


class DebateRound(BaseModel):
    """Single round in a bull/bear debate."""

    model_config = ConfigDict(from_attributes=True)

    round_num: int
    bull_argument: str
    bear_argument: str


class DebateResult(BaseModel):
    """Result of a bull/bear debate."""

    model_config = ConfigDict(from_attributes=True)

    rounds: list[DebateRound]
    judge_summary: str
    final_stance: Signal
    confidence: float
    key_contentions: list[str] = Field(default_factory=list)


class ValuationReport(BaseModel):
    """Valuation report model."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    ticker: str
    valuation_low: Decimal
    valuation_mid: Decimal
    valuation_high: Decimal
    pe_quantile: float
    bull_arguments: list[str]
    bear_arguments: list[str]
    key_assumptions: list[str]
    sensitivity_factors: dict = Field(default_factory=dict)
    competitor_comparison: dict = Field(default_factory=dict)
    human_approved: bool = False
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class PEBandResult(BaseModel):
    """PE band analysis result."""

    model_config = ConfigDict(from_attributes=True)

    ticker: str
    current_pe: float
    quantiles: dict[str, float]
    years_used: int
    current_quantile_position: float


class DCFAssumptions(BaseModel):
    """Assumptions for DCF valuation."""

    model_config = ConfigDict(from_attributes=True)

    growth_rate: float
    terminal_growth_rate: float
    wacc: float
    projection_years: int = 10


class DCFResult(BaseModel):
    """DCF valuation result."""

    model_config = ConfigDict(from_attributes=True)

    intrinsic_value: float
    sensitivity_matrix: dict
    assumptions: DCFAssumptions


class MonteCarloResult(BaseModel):
    """Monte Carlo simulation result."""

    model_config = ConfigDict(from_attributes=True)

    simulations: int
    percentiles: dict[str, float]
    mean_value: float
    std_dev: float


class MetricDefinition(BaseModel):
    """Custom metric definition."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    display_name: str
    data_type: str = "float"
    collection_mode: CollectionMode = CollectionMode.MANUAL
    alert_threshold: Optional[float] = None
    description: str = ""


class AlertRule(BaseModel):
    """Alert rule configuration."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    condition: str
    threshold: float
    severity: str = "warning"
    description: str = ""


class RealtimeQuote(BaseModel):
    """Realtime market quote."""

    model_config = ConfigDict(from_attributes=True)

    symbol: str
    price: float
    change_pct: float
    volume: Optional[int] = None
    timestamp: Optional[datetime] = None
