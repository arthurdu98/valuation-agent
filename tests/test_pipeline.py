from datetime import date
from decimal import Decimal

from src.graph.pipeline import ValuationPipeline
from src.schemas import Market


def test_pipeline_sequential_end_to_end():
    state = {
        "company": {"name": "贵州茅台"},
        "ticker": "600519",
        "industry": "白酒",
        "competitors": ["000858"],
        "financial_data": [
            {
                "ticker": "600519",
                "period": date(2024, 12, 31),
                "market": Market.A_SHARE,
                "revenue": Decimal("120"),
                "net_profit": Decimal("30"),
                "gross_margin": 65,
                "roe": 25,
                "total_assets": Decimal("200"),
                "total_liabilities": Decimal("50"),
                "operating_cashflow": Decimal("35"),
                "eps": Decimal("10"),
                "bvps": Decimal("50"),
            }
        ],
    }
    result = ValuationPipeline().run_sequential(state)
    assert "final_report" in result
    assert result["human_approved"] is False
