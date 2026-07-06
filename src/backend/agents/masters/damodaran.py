"""Aswath Damodaran master agent - narrative and numbers valuation."""

from src.backend.agents.masters.base import MasterAgent, CompanyAnalysisData
from src.backend.schemas import Signal


class DamodaranAgent(MasterAgent):
    """Aswath Damodaran's investment philosophy agent.

    Marries narrative with numbers. Disciplined valuation where
    narrative drives assumptions and numbers test the narrative.
    """

    @property
    def name(self) -> str:
        return "Aswath Damodaran"

    @property
    def philosophy(self) -> str:
        return (
            "Every investment is a story married to numbers. Disciplined valuation: "
            "narrative drives assumptions, numbers test the narrative."
        )

    def score(self, data: CompanyAnalysisData) -> dict:
        """Deterministic scoring based on Damodaran's criteria."""
        scores = {}

        latest = data.latest_financials

        # --- Revenue growth consistency (story: steady grower) ---
        # Consistent revenue growth supports a growth narrative
        if len(data.financials) >= 2:
            revenues = [
                float(f.revenue)
                for f in data.financials
                if f.revenue is not None
            ]
            if len(revenues) >= 2:
                # Check chronological growth (financials[0] is latest)
                chronological = list(reversed(revenues))
                growth_periods = sum(
                    1 for i in range(len(chronological) - 1)
                    if chronological[i + 1] > chronological[i]
                )
                # Steady growth: most periods show growth
                if growth_periods >= len(chronological) - 1:
                    scores["revenue_growth_consistency"] = 2
                elif growth_periods >= (len(chronological) - 1) * 0.5:
                    scores["revenue_growth_consistency"] = 1
                else:
                    scores["revenue_growth_consistency"] = 0

        # --- Margin expansion/contraction ---
        # Improving margins support the growth story
        if len(data.financials) >= 2:
            margins = [
                f.gross_margin
                for f in data.financials
                if f.gross_margin is not None
            ]
            if len(margins) >= 2:
                # margins[0] is latest
                if margins[0] > margins[-1]:
                    scores["margin_trend"] = 1
                elif margins[0] < margins[-1] - 5:
                    # Significant margin decline
                    scores["margin_trend"] = -1
                else:
                    scores["margin_trend"] = 0

        # --- PE vs growth (PEG-like analysis) ---
        # If PE < growth_rate * 100, stock is undervalued relative to growth
        if latest and data.pe_quantile is not None and len(data.financials) >= 2:
            revenues = [
                float(f.revenue)
                for f in data.financials
                if f.revenue is not None
            ]
            if len(revenues) >= 2 and revenues[-1] > 0:
                # Calculate approximate growth rate
                growth_rate = (revenues[0] - revenues[-1]) / revenues[-1]
                # Use pe_quantile as a proxy: low quantile + high growth = good
                if data.pe_quantile < 0.5 and growth_rate > 0.1:
                    scores["pe_vs_growth"] = 2
                elif data.pe_quantile < 0.7 and growth_rate > 0.05:
                    scores["pe_vs_growth"] = 1
                else:
                    scores["pe_vs_growth"] = 0

        # --- Capital efficiency ---
        # ROE > cost of equity proxy (10%) indicates value creation
        if latest and latest.roe is not None:
            if latest.roe > 10:
                scores["capital_efficiency"] = 1
            else:
                scores["capital_efficiency"] = 0

        # --- Narrative check: high growth but declining margins = story breaking ---
        # This is a red flag: the company is growing but at deteriorating economics
        if len(data.financials) >= 2:
            revenues = [
                float(f.revenue)
                for f in data.financials
                if f.revenue is not None
            ]
            margins = [
                f.gross_margin
                for f in data.financials
                if f.gross_margin is not None
            ]
            if len(revenues) >= 2 and len(margins) >= 2:
                revenue_growing = revenues[0] > revenues[-1]
                margin_declining = margins[0] < margins[-1] - 3
                if revenue_growing and margin_declining:
                    scores["narrative_break"] = -2

        return scores
