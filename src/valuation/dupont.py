from dataclasses import dataclass


@dataclass
class DuPontResult:
    roe: float
    net_profit_margin: float    # net_profit / revenue
    asset_turnover: float       # revenue / total_assets
    equity_multiplier: float    # total_assets / (total_assets - total_liabilities)

    @property
    def decomposition_str(self) -> str:
        return f"ROE = {self.net_profit_margin:.2%} × {self.asset_turnover:.2f} × {self.equity_multiplier:.2f} = {self.roe:.2%}"


class DuPontAnalyzer:
    """DuPont Analysis: ROE = Net Profit Margin × Asset Turnover × Equity Multiplier"""

    def analyze(self, revenue: float, net_profit: float, total_assets: float, total_liabilities: float) -> DuPontResult:
        """Decompose ROE into three components.

        Args:
            revenue: Total revenue
            net_profit: Net profit
            total_assets: Total assets
            total_liabilities: Total liabilities
        """
        equity = total_assets - total_liabilities
        if equity <= 0 or revenue <= 0 or total_assets <= 0:
            return DuPontResult(roe=0, net_profit_margin=0, asset_turnover=0, equity_multiplier=0)

        net_profit_margin = net_profit / revenue
        asset_turnover = revenue / total_assets
        equity_multiplier = total_assets / equity
        roe = net_profit_margin * asset_turnover * equity_multiplier

        return DuPontResult(
            roe=roe,
            net_profit_margin=net_profit_margin,
            asset_turnover=asset_turnover,
            equity_multiplier=equity_multiplier,
        )

    def analyze_trend(self, periods: list[dict]) -> list[DuPontResult]:
        """Analyze DuPont decomposition over multiple periods.
        Each dict needs: revenue, net_profit, total_assets, total_liabilities.
        """
        return [self.analyze(**p) for p in periods]
