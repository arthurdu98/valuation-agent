from datetime import date
from decimal import Decimal

import pandas as pd

from src.data.base import DataCollectionError
from src.data.collector import DataCollector
from src.schemas import FinancialStatements, Market


class FailingAdapter:
    def get_financial_statements(self, ticker: str, periods: int = 4):
        raise DataCollectionError("boom")


class WorkingAdapter:
    def get_financial_statements(self, ticker: str, periods: int = 4):
        return [
            FinancialStatements(
                ticker=ticker,
                period=date(2024, 12, 31),
                market=Market.A_SHARE,
                revenue=Decimal("100"),
                net_profit=Decimal("20"),
                gross_margin=0.6,
                roe=0.2,
                total_assets=Decimal("200"),
                total_liabilities=Decimal("80"),
                operating_cashflow=Decimal("25"),
                eps=Decimal("1"),
                bvps=Decimal("5"),
            )
        ]


def test_collector_fallback_chain():
    collector = DataCollector(
        adapters={Market.A_SHARE: [FailingAdapter(), WorkingAdapter()]}
    )
    result = collector.collect_company_data("600519", Market.A_SHARE)
    assert result is not None
    assert result[0].ticker == "600519"


def test_collector_failure_counter():
    collector = DataCollector(adapters={Market.US: [FailingAdapter()]})
    assert collector.collect_company_data("BAD", Market.US) is None
    assert collector.collect_company_data("BAD", Market.US) is None
    assert collector.collect_company_data("BAD", Market.US) is None
