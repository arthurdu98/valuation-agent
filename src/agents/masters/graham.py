"""Benjamin Graham master agent - margin of safety and value investing."""

from src.agents.masters.base import MasterAgent, CompanyAnalysisData
from src.schemas import Signal


class GrahamAgent(MasterAgent):
    """Benjamin Graham's investment philosophy agent.

    Focuses on margin of safety, buying below intrinsic value,
    asset protection, and earnings stability.
    """

    @property
    def name(self) -> str:
        return "Benjamin Graham"

    @property
    def philosophy(self) -> str:
        return (
            "Margin of safety is paramount. Buy below intrinsic value, "
            "focus on asset protection and earnings stability."
        )

    def score(self, data: CompanyAnalysisData) -> dict:
        """Deterministic scoring based on Graham's criteria."""
        scores = {}

        latest = data.latest_financials

        # --- Graham number vs current price ---
        # Graham number = sqrt(22.5 * EPS * BVPS)
        # Price below Graham number means significant margin of safety
        if data.graham_number is not None and data.current_price is not None:
            if data.current_price < data.graham_number:
                scores["graham_number"] = 3
            elif data.current_price < 1.5 * data.graham_number:
                scores["graham_number"] = 1
            else:
                scores["graham_number"] = 0

        # --- PE quantile (historical valuation context) ---
        # Low PE quantile means cheap relative to history
        if data.pe_quantile is not None:
            if data.pe_quantile < 0.25:
                scores["pe_quantile"] = 2
            elif data.pe_quantile < 0.5:
                scores["pe_quantile"] = 1
            elif data.pe_quantile > 0.9:
                scores["pe_quantile"] = -2
            else:
                scores["pe_quantile"] = 0

        # --- Current ratio (liquidity) ---
        # Graham required current ratio > 2 for safety
        if latest and latest.raw_data:
            current_ratio = latest.raw_data.get("current_ratio")
            if current_ratio is not None:
                if current_ratio > 2:
                    scores["current_ratio"] = 1
                elif current_ratio < 1:
                    scores["current_ratio"] = -1
                else:
                    scores["current_ratio"] = 0

        # --- Debt-to-equity ratio ---
        # Graham preferred low leverage: D/E < 0.5 is safe, > 1.5 is risky
        if latest and latest.total_assets and latest.total_liabilities is not None:
            total_assets = float(latest.total_assets)
            total_liab = float(latest.total_liabilities)
            equity = total_assets - total_liab
            if equity > 0:
                de_ratio = total_liab / equity
                if de_ratio < 0.5:
                    scores["debt_to_equity"] = 1
                elif de_ratio > 1.5:
                    scores["debt_to_equity"] = -2
                else:
                    scores["debt_to_equity"] = 0

        # --- Earnings stability ---
        # Graham demanded consistent positive earnings
        if len(data.financials) >= 2:
            profits = [
                float(f.net_profit)
                for f in data.financials
                if f.net_profit is not None
            ]
            if profits:
                all_positive = all(p > 0 for p in profits)
                if all_positive:
                    scores["earnings_stability"] = 1
                else:
                    scores["earnings_stability"] = -1

        return scores
