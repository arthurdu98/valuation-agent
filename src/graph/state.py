"""LangGraph state definition for the valuation pipeline."""

from dataclasses import dataclass
from typing import TypedDict

from src.agents.risk.falsifier import RiskAssessment
from src.schemas import (
    Company,
    DebateResult,
    FinancialStatements,
    MasterSignal,
    Signal,
    ValuationReport,
)


class ValuationState(TypedDict, total=False):
    """LangGraph state for the valuation pipeline."""

    # Input
    company: dict  # Company as dict
    ticker: str
    industry: str
    competitors: list[str]

    # L1 Analyst outputs
    financial_data: list[dict]
    industry_metrics: dict
    competitor_comparison: dict
    fundamentals_report: dict
    valuation_report_data: dict
    sentiment_report: dict
    industry_report: dict
    # Valuation numbers passed to L5
    pe_quantile: float | None
    dcf_value: float | None
    monte_carlo_percentiles: dict | None

    # L2 Master outputs
    master_signals: list[dict]  # list of MasterSignal as dicts

    # L3 Debate
    debate_result: dict  # DebateResult as dict

    # L4 Risk
    risk_assessment: dict

    # L5 Final
    final_report: dict  # ValuationReport as dict

    # Control
    human_approved: bool
    user_feedback: str
    error: str | None


@dataclass
class RunConfig:
    """Runtime options for a valuation pipeline run."""

    debate_rounds: int = 3
    thread_id: str = "valuation-default"
    timeout_seconds: int = 300
    llm_config_path: str = "configs/llm.yaml"
    require_human_approval: bool = True
