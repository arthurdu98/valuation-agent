from datetime import date
from decimal import Decimal

from src.backend.graph.pipeline import ValuationPipeline
from src.backend.schemas import Market


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


def _mock_state():
    return {
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


def test_pipeline_emits_progress_events_in_order():
    """Without an LLM router the pipeline degrades to rule-based, so this runs
    fast and lets us assert the progress event sequence deterministically."""
    events = []
    result = ValuationPipeline().run_sequential(_mock_state(), progress_cb=events.append)

    assert "final_report" in result
    # Every layer emits start then done, in L1->L5 order.
    stages_seen = [e["stage"] for e in events if e.get("status") in ("start", "done")]
    assert stages_seen == [
        "l1", "l1", "l2", "l2", "l3", "l3", "l4", "l4", "l5", "l5",
    ]
    # L2 emits one progress event per master (5 masters).
    l2_progress = [e for e in events if e["stage"] == "l2" and e.get("status") == "progress"]
    assert len(l2_progress) == 5
    assert l2_progress[0]["total"] == 5
    # L3 emits one progress event per debate round.
    l3_progress = [e for e in events if e["stage"] == "l3" and e.get("status") == "progress"]
    assert len(l3_progress) >= 1


def test_progress_cb_optional_backward_compatible():
    """run_sequential must still work with no progress_cb (default None)."""
    result = ValuationPipeline().run_sequential(_mock_state())
    assert "final_report" in result
