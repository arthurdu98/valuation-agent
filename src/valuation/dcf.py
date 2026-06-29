"""DCF (Discounted Cash Flow) valuation module.

Implements a two-stage DCF model with sensitivity analysis capabilities.
"""

import numpy as np

from src.schemas import DCFAssumptions, DCFResult


class DCFCalculator:
    """Two-stage Discounted Cash Flow calculator.

    Stage 1: Projects free cash flows for N years at a specified growth rate.
    Stage 2: Computes terminal value using the Gordon Growth Model.
    All cash flows are discounted back to present value at the WACC.
    """

    def calculate(
        self, free_cash_flows: list[float], assumptions: DCFAssumptions
    ) -> DCFResult:
        """Run a two-stage DCF valuation.

        Args:
            free_cash_flows: Historical free cash flows. The last element is used
                as the base for projections.
            assumptions: DCF model assumptions (growth_rate, terminal_growth_rate,
                wacc, projection_years).

        Returns:
            DCFResult with intrinsic value, sensitivity matrix, and assumptions.

        Raises:
            ValueError: If inputs are invalid (empty FCF list, wacc <= terminal
                growth rate, or non-positive WACC).
        """
        self._validate_inputs(free_cash_flows, assumptions)

        base_fcf = free_cash_flows[-1]
        growth_rate = assumptions.growth_rate
        wacc = assumptions.wacc
        terminal_growth_rate = assumptions.terminal_growth_rate
        projection_years = assumptions.projection_years

        # Stage 1: Project future FCFs and discount them
        projected_fcfs = np.array([
            base_fcf * (1 + growth_rate) ** n
            for n in range(1, projection_years + 1)
        ])

        discount_factors = np.array([
            1 / (1 + wacc) ** n for n in range(1, projection_years + 1)
        ])

        discounted_fcfs = projected_fcfs * discount_factors

        # Stage 2: Terminal value (Gordon Growth Model)
        last_projected_fcf = projected_fcfs[-1]
        terminal_value = (
            last_projected_fcf * (1 + terminal_growth_rate)
            / (wacc - terminal_growth_rate)
        )
        discounted_terminal_value = terminal_value / (1 + wacc) ** projection_years

        # Intrinsic value = sum of discounted FCFs + discounted terminal value
        intrinsic_value = float(np.sum(discounted_fcfs) + discounted_terminal_value)

        # Generate default sensitivity matrix
        sensitivity = self.sensitivity_matrix(free_cash_flows, assumptions)

        return DCFResult(
            intrinsic_value=intrinsic_value,
            sensitivity_matrix=sensitivity,
            assumptions=assumptions,
        )

    def sensitivity_matrix(
        self,
        free_cash_flows: list[float],
        base_assumptions: DCFAssumptions,
        growth_range: list[float] | None = None,
        wacc_range: list[float] | None = None,
    ) -> dict:
        """Generate a sensitivity matrix varying growth rate and WACC.

        Args:
            free_cash_flows: Historical free cash flows.
            base_assumptions: Base DCF assumptions to vary around.
            growth_range: List of growth rates to test. Defaults to
                [base-3%, base-1.5%, base, base+1.5%, base+3%].
            wacc_range: List of WACC values to test. Defaults to
                [base-2%, base-1%, base, base+1%, base+2%].

        Returns:
            Nested dict: {growth_rate: {wacc: intrinsic_value}}.
        """
        if growth_range is None:
            base_g = base_assumptions.growth_rate
            growth_range = [
                base_g - 0.03,
                base_g - 0.015,
                base_g,
                base_g + 0.015,
                base_g + 0.03,
            ]

        if wacc_range is None:
            base_w = base_assumptions.wacc
            wacc_range = [
                base_w - 0.02,
                base_w - 0.01,
                base_w,
                base_w + 0.01,
                base_w + 0.02,
            ]

        matrix: dict[float, dict[float, float]] = {}

        for growth in growth_range:
            matrix[round(growth, 6)] = {}
            for wacc in wacc_range:
                # Skip invalid combinations
                if wacc <= base_assumptions.terminal_growth_rate or wacc <= 0:
                    matrix[round(growth, 6)][round(wacc, 6)] = float("nan")
                    continue

                scenario_assumptions = DCFAssumptions(
                    growth_rate=growth,
                    terminal_growth_rate=base_assumptions.terminal_growth_rate,
                    wacc=wacc,
                    projection_years=base_assumptions.projection_years,
                )

                try:
                    value = self._calculate_intrinsic_value(
                        free_cash_flows, scenario_assumptions
                    )
                    matrix[round(growth, 6)][round(wacc, 6)] = value
                except ValueError:
                    matrix[round(growth, 6)][round(wacc, 6)] = float("nan")

        return matrix

    def calculate_from_financials(
        self,
        revenue: float,
        net_margin: float,
        capex_ratio: float,
        assumptions: DCFAssumptions,
    ) -> DCFResult:
        """Convenience method: estimate FCF from financials, then run DCF.

        Estimates free cash flow using a simplified formula:
            FCF = revenue * net_margin - revenue * capex_ratio

        Args:
            revenue: Annual revenue.
            net_margin: Net profit margin as a decimal (e.g. 0.15 for 15%).
            capex_ratio: Capital expenditure as a ratio of revenue (e.g. 0.05 for 5%).
            assumptions: DCF model assumptions.

        Returns:
            DCFResult with intrinsic value computed from estimated FCF.

        Raises:
            ValueError: If revenue is non-positive or margins are invalid.
        """
        if revenue <= 0:
            raise ValueError("Revenue must be positive.")
        if not (0 <= net_margin <= 1):
            raise ValueError("Net margin must be between 0 and 1.")
        if not (0 <= capex_ratio <= 1):
            raise ValueError("Capex ratio must be between 0 and 1.")

        fcf = revenue * net_margin - revenue * capex_ratio
        return self.calculate([fcf], assumptions)

    def _calculate_intrinsic_value(
        self, free_cash_flows: list[float], assumptions: DCFAssumptions
    ) -> float:
        """Internal helper to compute intrinsic value without sensitivity matrix.

        Args:
            free_cash_flows: Historical free cash flows.
            assumptions: DCF model assumptions.

        Returns:
            Intrinsic value as a float.
        """
        self._validate_inputs(free_cash_flows, assumptions)

        base_fcf = free_cash_flows[-1]
        growth_rate = assumptions.growth_rate
        wacc = assumptions.wacc
        terminal_growth_rate = assumptions.terminal_growth_rate
        projection_years = assumptions.projection_years

        # Project and discount FCFs
        projected_fcfs = np.array([
            base_fcf * (1 + growth_rate) ** n
            for n in range(1, projection_years + 1)
        ])

        discount_factors = np.array([
            1 / (1 + wacc) ** n for n in range(1, projection_years + 1)
        ])

        discounted_fcfs = projected_fcfs * discount_factors

        # Terminal value
        last_projected_fcf = projected_fcfs[-1]
        terminal_value = (
            last_projected_fcf * (1 + terminal_growth_rate)
            / (wacc - terminal_growth_rate)
        )
        discounted_terminal_value = terminal_value / (1 + wacc) ** projection_years

        return float(np.sum(discounted_fcfs) + discounted_terminal_value)

    @staticmethod
    def _validate_inputs(
        free_cash_flows: list[float], assumptions: DCFAssumptions
    ) -> None:
        """Validate DCF inputs.

        Args:
            free_cash_flows: List of free cash flows.
            assumptions: DCF assumptions to validate.

        Raises:
            ValueError: If any validation check fails.
        """
        if not free_cash_flows:
            raise ValueError("Free cash flows list must not be empty.")

        if assumptions.wacc <= 0:
            raise ValueError("WACC must be positive.")

        if assumptions.wacc <= assumptions.terminal_growth_rate:
            raise ValueError(
                "WACC must be greater than terminal growth rate. "
                f"Got wacc={assumptions.wacc}, "
                f"terminal_growth_rate={assumptions.terminal_growth_rate}."
            )

        if assumptions.projection_years <= 0:
            raise ValueError("Projection years must be positive.")
