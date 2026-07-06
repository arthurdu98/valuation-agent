"""Valuation analyst consolidating PE/DCF/Graham valuation signals.

Integrates multiple valuation methodologies to provide a comprehensive
assessment of intrinsic value and safety margins.
"""

from __future__ import annotations

import logging

from src.backend.valuation.dcf import DCFCalculator
from src.backend.valuation.graham import GrahamCalculator
from src.backend.valuation.pe_band import PEBandCalculator

logger = logging.getLogger(__name__)


class ValuationAnalyst:
    """Consolidates PE/DCF/Graham valuation signals.

    Combines outputs from multiple valuation models to produce a unified
    view of a company's valuation status, including Graham Number,
    safety margin, and PE band positioning.
    """

    def __init__(self) -> None:
        self._pe = PEBandCalculator()
        self._dcf = DCFCalculator()
        self._graham = GrahamCalculator()

    def analyze(
        self,
        financials: list,
        current_price: float = 0,
        pe_history=None,
    ) -> dict:
        """Run consolidated valuation analysis.

        Args:
            financials: List of FinancialStatements objects, most recent first.
            current_price: Current market price per share.
            pe_history: Optional historical PE series for band analysis.

        Returns:
            Dictionary with valuation signals including graham_number,
            safety_margin, and any PE band results when data is available.
        """
        result: dict = {}

        if financials:
            latest = financials[0]
            if latest.eps and latest.eps > 0:
                result["graham_number"] = self._graham.graham_number(
                    float(latest.eps), float(latest.bvps)
                )
                if current_price > 0:
                    result["safety_margin"] = self._graham.safety_margin(
                        current_price, result["graham_number"]
                    )

        return result
