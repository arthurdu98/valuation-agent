from datetime import date
from decimal import Decimal

from src.backend.agents.masters.base import CompanyAnalysisData
from src.backend.agents.masters.buffett import BuffettAgent
from src.backend.agents.masters.graham import GrahamAgent
from src.backend.schemas import FinancialStatements, Market, Signal


def _financials():
    return [
        FinancialStatements(
            ticker="600519",
            period=date(2024, 12, 31),
            market=Market.A_SHARE,
            revenue=Decimal("120"),
            net_profit=Decimal("30"),
            gross_margin=65,
            roe=25,
            total_assets=Decimal("200"),
            total_liabilities=Decimal("50"),
            operating_cashflow=Decimal("35"),
            eps=Decimal("10"),
            bvps=Decimal("50"),
            raw_data={"current_ratio": 2.5},
        ),
        FinancialStatements(
            ticker="600519",
            period=date(2023, 12, 31),
            market=Market.A_SHARE,
            revenue=Decimal("100"),
            net_profit=Decimal("25"),
            gross_margin=64,
            roe=24,
            total_assets=Decimal("180"),
            total_liabilities=Decimal("45"),
            operating_cashflow=Decimal("30"),
            eps=Decimal("9"),
            bvps=Decimal("45"),
        ),
    ]


def test_buffett_scores_quality_company():
    data = CompanyAnalysisData(
        ticker="600519",
        name="贵州茅台",
        industry="白酒",
        financials=_financials(),
        industry_metrics={"price_spread": 300},
    )
    signal = BuffettAgent().analyze(data)
    assert signal.signal == Signal.BULLISH


def test_graham_uses_margin_of_safety():
    data = CompanyAnalysisData(
        ticker="600519",
        name="贵州茅台",
        industry="白酒",
        financials=_financials(),
        pe_quantile=0.2,
        graham_number=100,
        current_price=80,
    )
    signal = GrahamAgent().analyze(data)
    assert signal.signal == Signal.BULLISH
