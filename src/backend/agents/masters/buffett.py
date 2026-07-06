"""Warren Buffett master agent - value investing with quality focus."""

from src.backend.agents.masters.base import MasterAgent, CompanyAnalysisData
from src.backend.schemas import Signal


class BuffettAgent(MasterAgent):
    """Warren Buffett's investment philosophy agent.

    Focuses on durable competitive advantages, pricing power,
    consistent earnings, and high returns on equity.
    """

    @property
    def name(self) -> str:
        return "Warren Buffett"

    @property
    def philosophy(self) -> str:
        return (
            "Buy wonderful companies at fair prices. Focus on durable competitive "
            "advantages, pricing power, consistent earnings, and high ROE."
        )

    def score(self, data: CompanyAnalysisData) -> dict:
        """Deterministic scoring based on Buffett's criteria."""
        scores = {}

        # --- ROE consistency ---
        # Latest ROE: >20% is excellent, >15% is good
        latest = data.latest_financials
        if latest and latest.roe is not None:
            if latest.roe > 20:
                scores["roe_level"] = 2
            elif latest.roe > 15:
                scores["roe_level"] = 1
            else:
                scores["roe_level"] = 0

            # ROE stability over 5 years (low std dev = stable)
            if len(data.financials) >= 3:
                roe_values = [
                    f.roe for f in data.financials if f.roe is not None
                ]
                if roe_values:
                    import statistics
                    roe_std = statistics.stdev(roe_values) if len(roe_values) > 1 else 0
                    # Stable ROE (std < 5%) gets a bonus
                    if roe_std < 5:
                        scores["roe_stability"] = 1
                    else:
                        scores["roe_stability"] = 0

        # --- Gross margin (pricing power indicator) ---
        # >60%: exceptional pricing power, >40%: good
        if latest and latest.gross_margin is not None:
            if latest.gross_margin > 60:
                scores["gross_margin"] = 2
            elif latest.gross_margin > 40:
                scores["gross_margin"] = 1
            else:
                scores["gross_margin"] = 0

        # --- Earnings growth consistency ---
        # 5-year positive net profit growth indicates quality business
        if len(data.financials) >= 2:
            profits = [
                float(f.net_profit)
                for f in data.financials
                if f.net_profit is not None
            ]
            if len(profits) >= 2:
                # Check if earnings have grown consistently (each period >= prior)
                # financials[0] is latest, so reverse for chronological order
                chronological = list(reversed(profits))
                all_growing = all(
                    chronological[i] <= chronological[i + 1]
                    for i in range(len(chronological) - 1)
                )
                if all_growing and len(chronological) >= 3:
                    scores["earnings_growth"] = 2
                elif chronological[-1] > chronological[0]:
                    # At least overall growth even if not monotonic
                    scores["earnings_growth"] = 1
                else:
                    scores["earnings_growth"] = 0

        # --- Debt ratio (conservative balance sheet) ---
        # total_liabilities / total_assets: <0.4 is safe, >0.7 is dangerous
        if latest and latest.total_assets and latest.total_liabilities is not None:
            total_assets = float(latest.total_assets)
            total_liab = float(latest.total_liabilities)
            if total_assets > 0:
                debt_ratio = total_liab / total_assets
                if debt_ratio < 0.4:
                    scores["debt_ratio"] = 1
                elif debt_ratio > 0.7:
                    scores["debt_ratio"] = -2
                else:
                    scores["debt_ratio"] = 0

        # --- Industry-specific: baijiu price spread ---
        # Higher price spread indicates strong brand and pricing power
        if "白酒" in data.industry or "baijiu" in data.industry.lower():
            price_spread = data.industry_metrics.get("price_spread")
            if price_spread is not None and price_spread > 200:
                scores["baijiu_price_spread"] = 1

        return scores
