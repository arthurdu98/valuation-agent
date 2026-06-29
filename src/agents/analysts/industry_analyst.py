"""Industry analyst for landscape and competitive position analysis.

Analyzes the broader industry context including market structure,
competitive dynamics, and a company's relative positioning.
"""

from __future__ import annotations

import logging

from src.data.competitor import CompetitorAnalyzer

logger = logging.getLogger(__name__)


class IndustryAnalyst:
    """Analyzes industry landscape and competitive position.

    Leverages the CompetitorAnalyzer to assess a company's standing
    within its industry, identifying key peers and competitive dynamics.
    """

    def __init__(self) -> None:
        self._competitor = CompetitorAnalyzer()

    def analyze(
        self,
        ticker: str,
        industry: str,
        competitors: list[str] | None = None,
    ) -> dict:
        """Analyze industry landscape and competitive position.

        Args:
            ticker: Stock ticker symbol of the target company.
            industry: Industry classification string.
            competitors: Optional list of known competitor tickers.
                If not provided, will attempt to discover peers.

        Returns:
            Dictionary with:
            - ticker: The analyzed company's ticker
            - industry: Industry classification
            - competitors: List of peer tickers
            - landscape: Industry landscape status or data
        """
        peers = competitors or self._competitor.get_competitors(ticker)
        comparison = self._competitor.compare_metrics(ticker, peers)
        return {
            "ticker": ticker,
            "industry": industry,
            "competitors": peers,
            "landscape": self._competitor.industry_landscape(industry),
            "comparison": comparison,
            "relative_position": self._competitor.relative_position(ticker, peers),
        }
