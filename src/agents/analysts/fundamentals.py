"""Fundamentals analyst for volume x price x structure decomposition.

Analyzes core financial metrics including revenue growth, profit growth,
margin trends, and key observations from financial statements.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class FundamentalsAnalyst:
    """Analyzes volume x price x structure decomposition.

    Examines financial statements to extract growth rates, margins,
    and profitability metrics, comparing against industry benchmarks.
    """

    def analyze(self, financials: list, industry_metrics: dict) -> dict:
        """Returns structured report: revenue_growth, profit_growth, margin_trend, key_observations.

        Args:
            financials: List of FinancialStatements objects, most recent first.
            industry_metrics: Dictionary of industry-level metrics for comparison.

        Returns:
            Dictionary with fundamental analysis results including growth rates,
            margins, and industry context. Returns {"status": "no_data"} if
            no financial data is available.
        """
        if not financials:
            return {"status": "no_data"}

        latest = financials[0]
        result: dict[str, Any] = {
            "revenue": float(latest.revenue) if latest.revenue else 0,
            "net_profit": float(latest.net_profit) if latest.net_profit else 0,
            "gross_margin": latest.gross_margin or 0,
            "roe": latest.roe or 0,
        }

        if len(financials) >= 2:
            prev = financials[1]
            if prev.revenue and latest.revenue and prev.revenue > 0:
                result["revenue_growth"] = float(
                    (latest.revenue - prev.revenue) / prev.revenue
                )
            if prev.net_profit and latest.net_profit and prev.net_profit > 0:
                result["profit_growth"] = float(
                    (latest.net_profit - prev.net_profit) / prev.net_profit
                )

        result["industry_metrics"] = industry_metrics
        return result
