"""Charlie Munger master agent - quality businesses with durable moats."""

import statistics

from src.backend.agents.masters.base import MasterAgent, CompanyAnalysisData
from src.backend.schemas import Signal


class MungerAgent(MasterAgent):
    """Charlie Munger's investment philosophy agent.

    Invests in high-quality businesses with durable moats,
    honest management, and long runways. Avoids complexity and leverage.
    """

    @property
    def name(self) -> str:
        return "Charlie Munger"

    @property
    def philosophy(self) -> str:
        return (
            "Invest in high-quality businesses with durable moats, honest management, "
            "and long runways. Avoid complexity and leverage."
        )

    def score(self, data: CompanyAnalysisData) -> dict:
        """Deterministic scoring based on Munger's criteria."""
        scores = {}

        latest = data.latest_financials

        # --- Gross margin stability ---
        # Low standard deviation in gross margins = predictable, moat-protected business
        if len(data.financials) >= 2:
            margins = [
                f.gross_margin
                for f in data.financials
                if f.gross_margin is not None
            ]
            if len(margins) >= 2:
                margin_std = statistics.stdev(margins)
                if margin_std < 5:
                    scores["margin_stability"] = 2
                elif margin_std < 10:
                    scores["margin_stability"] = 1
                else:
                    scores["margin_stability"] = 0

        # --- Revenue CAGR (long runway indicator) ---
        # >20%: exceptional growth runway, >10%: good runway
        if len(data.financials) >= 2:
            revenues = [
                float(f.revenue)
                for f in data.financials
                if f.revenue is not None
            ]
            if len(revenues) >= 2 and revenues[-1] > 0:
                # revenues[0] is latest, revenues[-1] is oldest
                n_periods = len(revenues) - 1
                if n_periods > 0:
                    cagr = (revenues[0] / revenues[-1]) ** (1 / n_periods) - 1
                    cagr_pct = cagr * 100
                    if cagr_pct > 20:
                        scores["revenue_cagr"] = 2
                    elif cagr_pct > 10:
                        scores["revenue_cagr"] = 1
                    else:
                        scores["revenue_cagr"] = 0

        # --- Low leverage (avoid leveraged businesses) ---
        # Debt ratio < 0.4 means conservative financing
        if latest and latest.total_assets and latest.total_liabilities is not None:
            total_assets = float(latest.total_assets)
            total_liab = float(latest.total_liabilities)
            if total_assets > 0:
                debt_ratio = total_liab / total_assets
                if debt_ratio < 0.4:
                    scores["low_leverage"] = 1
                elif debt_ratio > 0.6:
                    scores["low_leverage"] = -1
                else:
                    scores["low_leverage"] = 0

        # --- Business simplicity ---
        # Simple, understandable businesses in focused industries
        simple_industries = ["白酒", "中药", "调味品", "乳制品"]
        if any(ind in data.industry for ind in simple_industries):
            scores["business_simplicity"] = 1
        else:
            scores["business_simplicity"] = 0

        # --- Moat indicator ---
        # Consistent high margins + growth = evidence of durable moat
        has_high_margins = False
        has_growth = False

        if latest and latest.gross_margin is not None:
            if latest.gross_margin > 40:
                has_high_margins = True

        if len(data.financials) >= 2:
            revenues = [
                float(f.revenue)
                for f in data.financials
                if f.revenue is not None
            ]
            if len(revenues) >= 2 and revenues[-1] > 0:
                overall_growth = (revenues[0] - revenues[-1]) / revenues[-1]
                if overall_growth > 0.1:
                    has_growth = True

        if has_high_margins and has_growth:
            scores["moat_indicator"] = 2
        elif has_high_margins or has_growth:
            scores["moat_indicator"] = 1
        else:
            scores["moat_indicator"] = 0

        return scores
