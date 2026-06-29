"""PE historical quantile band calculator for valuation assessment."""

import numpy as np
import pandas as pd

from src.schemas import PEBandResult


class PEBandCalculator:
    """Calculate PE historical quantile bands for valuation assessment."""

    def calculate(
        self, pe_series: pd.Series, current_pe: float, years: int = 5
    ) -> PEBandResult:
        """Calculate PE quantile band.

        Args:
            pe_series: Historical PE ratios indexed by date.
            current_pe: Current PE ratio.
            years: Number of years of history to use (3, 5, or 10).

        Returns:
            PEBandResult with quantile positions.
        """
        # Filter to requested years
        if not pe_series.empty:
            cutoff = pe_series.index.max() - pd.DateOffset(years=years)
            filtered = pe_series[pe_series.index >= cutoff].dropna()
        else:
            filtered = pe_series

        if filtered.empty or len(filtered) < 10:
            # Not enough data
            return PEBandResult(
                ticker="",
                current_pe=current_pe,
                quantiles={"p10": 0, "p25": 0, "p50": 0, "p75": 0, "p90": 0},
                years_used=years,
                current_quantile_position=0.5,
            )

        # Calculate quantiles
        quantiles = {
            "p10": float(np.percentile(filtered, 10)),
            "p25": float(np.percentile(filtered, 25)),
            "p50": float(np.percentile(filtered, 50)),
            "p75": float(np.percentile(filtered, 75)),
            "p90": float(np.percentile(filtered, 90)),
        }

        # Calculate current position (percentile rank)
        current_quantile_position = float(
            (filtered < current_pe).sum() / len(filtered)
        )

        return PEBandResult(
            ticker="",
            current_pe=current_pe,
            quantiles=quantiles,
            years_used=years,
            current_quantile_position=current_quantile_position,
        )

    def calculate_multi_period(
        self, pe_series: pd.Series, current_pe: float, ticker: str = ""
    ) -> dict[int, PEBandResult]:
        """Calculate PE bands for 3, 5, and 10 year periods.

        Args:
            pe_series: Historical PE ratios indexed by date.
            current_pe: Current PE ratio.
            ticker: Stock ticker symbol.

        Returns:
            Dictionary mapping years to PEBandResult.
        """
        results: dict[int, PEBandResult] = {}
        for years in [3, 5, 10]:
            result = self.calculate(pe_series, current_pe, years)
            result.ticker = ticker
            results[years] = result
        return results

    def is_undervalued(self, result: PEBandResult, threshold: float = 0.1) -> bool:
        """Check if current PE is below the 10th percentile.

        Args:
            result: PEBandResult from calculate().
            threshold: Quantile position threshold (default 0.1 = bottom 10%).

        Returns:
            True if current PE is at or below the threshold.
        """
        return result.current_quantile_position <= threshold

    def is_overvalued(self, result: PEBandResult, threshold: float = 0.9) -> bool:
        """Check if current PE is above the 90th percentile.

        Args:
            result: PEBandResult from calculate().
            threshold: Quantile position threshold (default 0.9 = top 10%).

        Returns:
            True if current PE is at or above the threshold.
        """
        return result.current_quantile_position >= threshold
