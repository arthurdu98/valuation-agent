"""Base protocol and utilities for market data adapters.

This module defines the DataAdapter protocol interface that unifies all market
data sources (Tushare, BaoStock, AKShare, etc.) behind a common API, along with
a fallback decorator for resilient data fetching and a shared exception class.
"""

from __future__ import annotations

import functools
import logging
import time
from datetime import date
from typing import Protocol, runtime_checkable

import pandas as pd

from src.backend.schemas import FinancialStatements

logger = logging.getLogger(__name__)


# --- Exceptions ---


class DataCollectionError(Exception):
    """Raised when a data collection operation fails.

    Use this for errors in the data layer such as network failures,
    API rate limits, missing data, or malformed responses from
    upstream data providers.
    """

    pass


# --- Protocol ---


@runtime_checkable
class DataAdapter(Protocol):
    """Protocol interface that all market data adapters must satisfy.

    Implementations provide access to financial statements, price history,
    key metrics, and macro indicators from various data sources (Tushare,
    BaoStock, AKShare, etc.).

    Example:
        class TushareAdapter:
            def get_financial_statements(self, ticker: str, periods: int = 4) -> list[FinancialStatements]:
                ...

            def get_price_history(self, ticker: str, start: date, end: date) -> pd.DataFrame:
                ...

            def get_key_metrics(self, ticker: str) -> dict[str, float]:
                ...

            def get_macro_indicators(self) -> dict[str, pd.Series]:
                ...
    """

    def get_financial_statements(
        self, ticker: str, periods: int = 4
    ) -> list[FinancialStatements]:
        """Fetch financial statements for the last N periods.

        Args:
            ticker: Stock ticker symbol (e.g., "600519.SH").
            periods: Number of reporting periods to retrieve (default 4,
                     typically representing one year of quarterly reports).

        Returns:
            List of FinancialStatements ordered from most recent to oldest.

        Raises:
            DataCollectionError: If the data cannot be fetched or parsed.
        """
        ...

    def get_price_history(
        self, ticker: str, start: date, end: date
    ) -> pd.DataFrame:
        """Fetch daily price history for a given date range.

        Args:
            ticker: Stock ticker symbol (e.g., "600519.SH").
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            DataFrame with columns: date, open, high, low, close, volume.
            Rows are sorted by date ascending.

        Raises:
            DataCollectionError: If the data cannot be fetched or parsed.
        """
        ...

    def get_key_metrics(self, ticker: str) -> dict[str, float]:
        """Fetch key financial metrics for a stock.

        Args:
            ticker: Stock ticker symbol (e.g., "600519.SH").

        Returns:
            Dictionary of metric name to value. Common keys include:
            - pe: Price-to-Earnings ratio
            - pb: Price-to-Book ratio
            - ps: Price-to-Sales ratio
            - dividend_yield: Annual dividend yield
            - market_cap: Total market capitalization
            - roe: Return on Equity
            - debt_to_equity: Debt-to-Equity ratio

        Raises:
            DataCollectionError: If the data cannot be fetched or parsed.
        """
        ...

    def get_macro_indicators(self) -> dict[str, pd.Series]:
        """Fetch relevant macro indicators for this market.

        Returns:
            Dictionary mapping indicator names to time-series data.
            Common keys include:
            - gdp_growth: GDP growth rate series
            - cpi: Consumer Price Index series
            - pmi: Purchasing Managers Index series
            - interest_rate: Benchmark interest rate series
            - m2_growth: M2 money supply growth series

        Raises:
            DataCollectionError: If the data cannot be fetched or parsed.
        """
        ...


# --- Fallback Decorator ---


def with_fallback(
    fallback_adapters: list,
    max_retries: int = 3,
    retry_delay: float = 1.0,
):
    """Decorator that tries fallback adapters when the primary fails.

    Wraps a function whose first argument is a DataAdapter. If the primary
    adapter (passed as the first positional arg) raises an exception, the
    decorator retries with exponential backoff, then moves on to each
    fallback adapter in order.

    Args:
        fallback_adapters: Ordered list of backup DataAdapter instances to
            try if the primary adapter fails.
        max_retries: Maximum number of attempts per adapter (default 3).
        retry_delay: Base delay in seconds between retries. Actual delay
            is ``retry_delay * (attempt_number)`` for linear backoff.

    Usage:
        @with_fallback([TushareAdapter(), BaoStockAdapter()])
        def get_data(adapter: DataAdapter, ticker: str):
            return adapter.get_financial_statements(ticker)

    Raises:
        RuntimeError: If all adapters exhaust their retries.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            adapters = (
                [args[0]] + fallback_adapters if args else fallback_adapters
            )
            last_error: Exception | None = None

            for adapter in adapters:
                for attempt in range(max_retries):
                    try:
                        new_args = (
                            (adapter,) + args[1:] if args else args
                        )
                        return func(*new_args, **kwargs)
                    except Exception as e:
                        last_error = e
                        logger.warning(
                            f"Adapter {type(adapter).__name__} attempt "
                            f"{attempt + 1} failed: {e}"
                        )
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay * (attempt + 1))

                logger.error(
                    f"Adapter {type(adapter).__name__} exhausted all retries"
                )

            raise RuntimeError(
                f"All adapters failed. Last error: {last_error}"
            )

        return wrapper

    return decorator
