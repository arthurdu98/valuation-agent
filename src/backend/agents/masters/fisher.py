"""Philip Fisher master agent - growth investing and scuttlebutt method."""

from src.backend.agents.masters.base import MasterAgent, CompanyAnalysisData
from src.backend.schemas import Signal


class FisherAgent(MasterAgent):
    """Philip Fisher's investment philosophy agent.

    Scuttlebutt investing: judges management quality, R&D capability,
    and corporate culture through qualitative evidence.
    Note: scoring is more conservative without RAG evidence in production.
    """

    @property
    def name(self) -> str:
        return "Philip Fisher"

    @property
    def philosophy(self) -> str:
        return (
            "Scuttlebutt investing: judge management quality, R&D capability, "
            "and corporate culture through qualitative evidence."
        )

    def score(self, data: CompanyAnalysisData) -> dict:
        """Deterministic scoring based on Fisher's criteria.

        Note: Fisher's approach relies heavily on qualitative scuttlebutt.
        This scoring is conservative without RAG evidence; in production
        the narrate() step incorporates qualitative signals.
        """
        scores = {}

        latest = data.latest_financials

        # --- Revenue growth rate (management execution proxy) ---
        # >15%: excellent execution, >8%: acceptable
        if len(data.financials) >= 2:
            revenues = [
                float(f.revenue)
                for f in data.financials
                if f.revenue is not None
            ]
            if len(revenues) >= 2 and revenues[-1] > 0:
                # Latest vs oldest growth rate (annualized if possible)
                n_periods = len(revenues) - 1
                if n_periods > 0:
                    cagr = (revenues[0] / revenues[-1]) ** (1 / n_periods) - 1
                    growth_pct = cagr * 100
                    if growth_pct > 15:
                        scores["revenue_growth"] = 2
                    elif growth_pct > 8:
                        scores["revenue_growth"] = 1
                    else:
                        scores["revenue_growth"] = 0

        # --- R&D ratio (innovation capability) ---
        # If R&D data available, >5% of revenue indicates innovation focus
        if latest and latest.raw_data:
            rd_expense = latest.raw_data.get("rd_expense") or latest.raw_data.get("r_and_d")
            if rd_expense is not None and latest.revenue:
                revenue_val = float(latest.revenue)
                if revenue_val > 0:
                    rd_ratio = float(rd_expense) / revenue_val * 100
                    if rd_ratio > 5:
                        scores["rd_ratio"] = 1
                    else:
                        scores["rd_ratio"] = 0

        # --- Gross margin trend (management quality signal) ---
        # Improving margins indicate strong management and competitive position
        if len(data.financials) >= 2:
            margins = [
                f.gross_margin
                for f in data.financials
                if f.gross_margin is not None
            ]
            if len(margins) >= 2:
                # margins[0] is latest, margins[-1] is oldest
                if margins[0] > margins[-1]:
                    scores["margin_trend"] = 1
                elif margins[0] < margins[-1] - 3:
                    # Significant decline signals management issues
                    scores["margin_trend"] = -1
                else:
                    scores["margin_trend"] = 0

        # --- Employee productivity proxy ---
        # Revenue growth outpacing asset growth = efficient management
        if len(data.financials) >= 2:
            revenues = [
                float(f.revenue)
                for f in data.financials
                if f.revenue is not None
            ]
            assets = [
                float(f.total_assets)
                for f in data.financials
                if f.total_assets is not None
            ]
            if len(revenues) >= 2 and len(assets) >= 2:
                if revenues[-1] > 0 and assets[-1] > 0:
                    rev_growth = (revenues[0] - revenues[-1]) / revenues[-1]
                    asset_growth = (assets[0] - assets[-1]) / assets[-1]
                    if rev_growth > asset_growth:
                        scores["employee_productivity"] = 1
                    else:
                        scores["employee_productivity"] = 0

        return scores
