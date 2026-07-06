"""Monte Carlo simulation for valuation uncertainty quantification."""

import numpy as np

from src.backend.schemas import DCFAssumptions, MonteCarloResult
from src.backend.valuation.dcf import DCFCalculator


class MonteCarloValuation:
    """Monte Carlo simulation for valuation uncertainty quantification."""

    def __init__(self, n_simulations: int = 10000, seed: int | None = 42):
        self.n_simulations = n_simulations
        self.rng = np.random.default_rng(seed)
        self._dcf_calculator = DCFCalculator()

    def simulate(
        self,
        base_fcf: float,
        growth_rate_mean: float,
        growth_rate_std: float,
        wacc_mean: float,
        wacc_std: float,
        terminal_growth_mean: float = 0.03,
        terminal_growth_std: float = 0.005,
        projection_years: int = 10,
    ) -> MonteCarloResult:
        """Run Monte Carlo DCF simulation with GBM-sampled parameters.

        Samples growth_rate, wacc, and terminal_growth from normal distributions,
        runs DCF for each sample, and returns distribution statistics.
        """
        values = []

        for _ in range(self.n_simulations):
            # Sample parameters
            growth = self.rng.normal(growth_rate_mean, growth_rate_std)
            wacc = self.rng.normal(wacc_mean, wacc_std)
            terminal_growth = self.rng.normal(terminal_growth_mean, terminal_growth_std)

            # Ensure valid parameters
            wacc = max(wacc, terminal_growth + 0.01)  # wacc must exceed terminal growth
            wacc = max(wacc, 0.01)

            assumptions = DCFAssumptions(
                growth_rate=growth,
                terminal_growth_rate=terminal_growth,
                wacc=wacc,
                projection_years=projection_years,
            )

            try:
                result = self._dcf_calculator.calculate([base_fcf], assumptions)
                if result.intrinsic_value > 0:
                    values.append(result.intrinsic_value)
            except (ValueError, ZeroDivisionError):
                continue

        if not values:
            return MonteCarloResult(simulations=0, percentiles={}, mean_value=0, std_dev=0)

        arr = np.array(values)
        percentiles = {
            "p10": float(np.percentile(arr, 10)),
            "p25": float(np.percentile(arr, 25)),
            "p50": float(np.percentile(arr, 50)),
            "p75": float(np.percentile(arr, 75)),
            "p90": float(np.percentile(arr, 90)),
        }

        return MonteCarloResult(
            simulations=len(values),
            percentiles=percentiles,
            mean_value=float(arr.mean()),
            std_dev=float(arr.std()),
        )
