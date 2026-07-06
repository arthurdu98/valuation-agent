import math


class GrahamCalculator:
    """Graham Number and safety margin calculations."""

    def graham_number(self, eps: float, bvps: float) -> float:
        """Calculate Graham Number = sqrt(22.5 * EPS * BVPS).

        Returns 0 if either EPS or BVPS is negative.
        """
        if eps <= 0 or bvps <= 0:
            return 0.0
        return math.sqrt(22.5 * eps * bvps)

    def safety_margin(self, current_price: float, intrinsic_value: float) -> float:
        """Calculate safety margin percentage.

        Returns: (intrinsic_value - current_price) / intrinsic_value
        Positive means undervalued, negative means overvalued.
        """
        if intrinsic_value <= 0:
            return 0.0
        return (intrinsic_value - current_price) / intrinsic_value

    def ncav(self, current_assets: float, total_liabilities: float) -> float:
        """Net Current Asset Value = Current Assets - Total Liabilities.

        Graham's bargain criterion: buy when price < 2/3 NCAV per share.
        """
        return current_assets - total_liabilities

    def ncav_per_share(self, current_assets: float, total_liabilities: float, shares_outstanding: float) -> float:
        """NCAV per share."""
        if shares_outstanding <= 0:
            return 0.0
        return self.ncav(current_assets, total_liabilities) / shares_outstanding

    def is_graham_bargain(self, current_price: float, eps: float, bvps: float) -> bool:
        """Check if stock is below Graham Number (bargain territory)."""
        gn = self.graham_number(eps, bvps)
        return gn > 0 and current_price < gn
