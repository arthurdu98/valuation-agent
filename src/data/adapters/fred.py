"""FRED (Federal Reserve Economic Data) adapter for macro economic data."""

import logging
from datetime import date
from typing import Optional

import pandas as pd
from fredapi import Fred

from src.config import settings
from src.db.models import IndustryMetricModel

logger = logging.getLogger(__name__)


class FREDAdapter:
    """Supplementary macro data source using the FRED API.

    Provides access to Federal Reserve Economic Data including
    interest rates, inflation metrics, employment data, and treasury yields.
    """

    SERIES_MAP: dict[str, str] = {
        # Interest rates
        "fed_funds_rate": "FEDFUNDS",
        "treasury_10y": "DGS10",
        "treasury_2y": "DGS2",
        # Commodities
        "gold_price": "GOLDAMGBD228NLBM",
        # Inflation
        "cpi": "CPIAUCSL",
        "core_cpi": "CPILFESL",
        # Employment
        "unemployment": "UNRATE",
        # Money supply
        "m2": "M2SL",
        # Consumer spending
        "pce": "PCE",
        # Output
        "real_gdp": "GDPC1",
    }

    YIELD_CURVE_SERIES: dict[str, str] = {
        "1m": "DGS1MO",
        "3m": "DGS3MO",
        "6m": "DGS6MO",
        "1y": "DGS1",
        "2y": "DGS2",
        "5y": "DGS5",
        "10y": "DGS10",
        "30y": "DGS30",
    }

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the FRED adapter.

        Args:
            api_key: FRED API key. Falls back to settings.fred_api_key if not provided.
        """
        self._api_key = api_key or settings.fred_api_key
        if not self._api_key:
            raise ValueError(
                "FRED API key is required. Set fred_api_key in .env or pass explicitly."
            )
        self._client = Fred(api_key=self._api_key)
        logger.info("FREDAdapter initialized successfully.")

    def get_series(
        self,
        series_id: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> pd.Series:
        """Fetch a single FRED series by ID.

        Args:
            series_id: FRED series identifier (e.g. "FEDFUNDS").
            start: Start date for the data range.
            end: End date for the data range.

        Returns:
            pandas Series indexed by date.

        Raises:
            ValueError: If the series cannot be fetched.
        """
        try:
            logger.debug("Fetching FRED series: %s", series_id)
            observation_start = start.isoformat() if start else None
            observation_end = end.isoformat() if end else None

            data = self._client.get_series(
                series_id,
                observation_start=observation_start,
                observation_end=observation_end,
            )
            logger.info(
                "Fetched %d observations for series %s", len(data), series_id
            )
            return data
        except Exception as e:
            logger.error("Failed to fetch FRED series %s: %s", series_id, e)
            raise ValueError(
                f"Failed to fetch FRED series '{series_id}': {e}"
            ) from e

    def get_macro_indicators(self) -> dict[str, pd.Series]:
        """Fetch all commonly tracked macro indicators.

        Returns:
            Dict mapping friendly names (e.g. "fed_funds_rate") to pandas Series.
        """
        results: dict[str, pd.Series] = {}
        for name, series_id in self.SERIES_MAP.items():
            try:
                results[name] = self.get_series(series_id)
            except ValueError:
                logger.warning(
                    "Skipping indicator '%s' (series %s) due to fetch error.",
                    name,
                    series_id,
                )
        logger.info(
            "Fetched %d/%d macro indicators.", len(results), len(self.SERIES_MAP)
        )
        return results

    def get_yield_curve(self) -> dict[str, float]:
        """Fetch current yields for standard treasury maturities.

        Fetches the latest available value for 1m, 3m, 6m, 1y, 2y, 5y, 10y, 30y
        treasury yields.

        Returns:
            Dict mapping maturity labels to latest yield values.
        """
        yields: dict[str, float] = {}
        for maturity, series_id in self.YIELD_CURVE_SERIES.items():
            try:
                data = self.get_series(series_id)
                # Drop NaN values and get the most recent observation
                valid_data = data.dropna()
                if not valid_data.empty:
                    yields[maturity] = float(valid_data.iloc[-1])
                else:
                    logger.warning(
                        "No valid data for yield curve maturity %s (series %s).",
                        maturity,
                        series_id,
                    )
            except ValueError:
                logger.warning(
                    "Skipping yield curve maturity %s (series %s) due to fetch error.",
                    maturity,
                    series_id,
                )
        logger.info(
            "Fetched %d/%d yield curve points.",
            len(yields),
            len(self.YIELD_CURVE_SERIES),
        )
        return yields

    def store_macro_indicators(self, db_session, start: Optional[date] = None) -> int:
        """Fetch configured series and store observations in industry_metrics."""
        inserted = 0
        for name, series_id in self.SERIES_MAP.items():
            try:
                series = self.get_series(series_id, start=start).dropna()
            except ValueError:
                continue
            for recorded_at, value in series.items():
                db_session.add(
                    IndustryMetricModel(
                        ticker="MACRO_US",
                        metric_name=name,
                        metric_value=float(value),
                        recorded_at=recorded_at.to_pydatetime()
                        if hasattr(recorded_at, "to_pydatetime")
                        else recorded_at,
                        source="fred",
                        confidence=1.0,
                    )
                )
                inserted += 1
        db_session.commit()
        return inserted
