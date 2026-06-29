"""US market data adapter using yfinance.

Provides access to US stock financial statements, price history,
and key metrics via the Yahoo Finance API (yfinance library).
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

import pandas as pd
import yfinance as yf

from src.data.base import DataCollectionError
from src.schemas import FinancialStatements, Market

logger = logging.getLogger(__name__)


class USAdapter:
    """US market data adapter satisfying the DataAdapter protocol.

    Uses yfinance to fetch financial data for US-listed stocks.
    Ticker format: "GOOGL", "AAPL", "MSFT", etc.
    """

    def get_financial_statements(
        self, ticker: str, periods: int = 4
    ) -> list[FinancialStatements]:
        """Fetch quarterly financial statements for a US stock.

        Args:
            ticker: US stock ticker symbol (e.g., "AAPL", "GOOGL").
            periods: Number of quarterly periods to retrieve (default 4).

        Returns:
            List of FinancialStatements ordered from most recent to oldest.

        Raises:
            DataCollectionError: If data cannot be fetched or parsed.
        """
        try:
            yf_ticker = yf.Ticker(ticker)

            financials = yf_ticker.quarterly_financials
            balance_sheet = yf_ticker.quarterly_balance_sheet
            cashflow = yf_ticker.quarterly_cashflow

            if financials is None or financials.empty:
                raise DataCollectionError(
                    f"No quarterly financials available for {ticker}"
                )

            # Get available periods (columns are dates)
            available_periods = financials.columns[:periods]
            results: list[FinancialStatements] = []

            for period_date in available_periods:
                try:
                    stmt = self._build_statement(
                        ticker=ticker,
                        period_date=period_date,
                        financials=financials,
                        balance_sheet=balance_sheet,
                        cashflow=cashflow,
                    )
                    results.append(stmt)
                except Exception as e:
                    logger.warning(
                        f"Skipping period {period_date} for {ticker}: {e}"
                    )
                    continue

            if not results:
                raise DataCollectionError(
                    f"Could not parse any financial statements for {ticker}"
                )

            return results

        except DataCollectionError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch financial statements for {ticker}: {e}")
            raise DataCollectionError(
                f"Failed to fetch financial statements for {ticker}: {e}"
            ) from e

    def get_price_history(
        self, ticker: str, start: date, end: date
    ) -> pd.DataFrame:
        """Fetch daily price history for a US stock.

        Args:
            ticker: US stock ticker symbol (e.g., "AAPL", "GOOGL").
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            DataFrame with columns: date, open, high, low, close, volume.
            Rows sorted by date ascending.

        Raises:
            DataCollectionError: If data cannot be fetched or parsed.
        """
        try:
            df = yf.download(
                ticker,
                start=start.isoformat(),
                end=end.isoformat(),
                progress=False,
            )

            if df is None or df.empty:
                raise DataCollectionError(
                    f"No price history available for {ticker} "
                    f"from {start} to {end}"
                )

            # Flatten multi-level columns if present (yfinance sometimes returns them)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Normalize to expected column format
            df = df.reset_index()
            df.columns = [col.lower() for col in df.columns]

            # Ensure required columns exist
            expected_cols = ["date", "open", "high", "low", "close", "volume"]
            missing = [c for c in expected_cols if c not in df.columns]
            if missing:
                raise DataCollectionError(
                    f"Missing columns in price data for {ticker}: {missing}"
                )

            df = df[expected_cols].sort_values("date").reset_index(drop=True)
            return df

        except DataCollectionError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch price history for {ticker}: {e}")
            raise DataCollectionError(
                f"Failed to fetch price history for {ticker}: {e}"
            ) from e

    def get_key_metrics(self, ticker: str) -> dict[str, float]:
        """Fetch key financial metrics for a US stock.

        Args:
            ticker: US stock ticker symbol (e.g., "AAPL", "GOOGL").

        Returns:
            Dictionary with keys: pe, pb, market_cap, dividend_yield.

        Raises:
            DataCollectionError: If data cannot be fetched or parsed.
        """
        try:
            yf_ticker = yf.Ticker(ticker)
            info = yf_ticker.info

            if not info:
                raise DataCollectionError(
                    f"No info available for {ticker}"
                )

            metrics: dict[str, float] = {}

            # PE ratio
            pe = info.get("trailingPE") or info.get("forwardPE")
            if pe is not None:
                metrics["pe"] = float(pe)

            # PB ratio
            pb = info.get("priceToBook")
            if pb is not None:
                metrics["pb"] = float(pb)

            # Market capitalization
            market_cap = info.get("marketCap")
            if market_cap is not None:
                metrics["market_cap"] = float(market_cap)

            # Dividend yield
            dividend_yield = info.get("dividendYield")
            if dividend_yield is not None:
                metrics["dividend_yield"] = float(dividend_yield)

            return metrics

        except DataCollectionError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch key metrics for {ticker}: {e}")
            raise DataCollectionError(
                f"Failed to fetch key metrics for {ticker}: {e}"
            ) from e

    def get_macro_indicators(self) -> dict[str, pd.Series]:
        """Return macro indicators for the US market.

        Note: US macro indicators (GDP, CPI, interest rates, etc.) are
        sourced from the FRED adapter instead. This method returns an
        empty dict as a placeholder to satisfy the DataAdapter protocol.

        Returns:
            Empty dictionary. Use the FRED adapter for US macro data.
        """
        # US macro indicators come from the FRED adapter (Federal Reserve
        # Economic Data) which provides more comprehensive and reliable
        # macro data. See src/data/adapters/fred.py when implemented.
        return {}

    # --- Private Helpers ---

    def _safe_get(
        self, df: pd.DataFrame | None, row: str, col, default=None
    ):
        """Safely extract a value from a DataFrame.

        Returns default if the DataFrame is None, the row/col doesn't exist,
        or the value is NaN.
        """
        if df is None or df.empty:
            return default
        try:
            value = df.loc[row, col] if row in df.index else None
            if value is None or pd.isna(value):
                return default
            return value
        except (KeyError, TypeError):
            return default

    def _build_statement(
        self,
        ticker: str,
        period_date,
        financials: pd.DataFrame,
        balance_sheet: pd.DataFrame | None,
        cashflow: pd.DataFrame | None,
    ) -> FinancialStatements:
        """Build a FinancialStatements instance from yfinance DataFrames.

        Args:
            ticker: Stock ticker symbol.
            period_date: Column date from the quarterly data.
            financials: Quarterly income statement DataFrame.
            balance_sheet: Quarterly balance sheet DataFrame.
            cashflow: Quarterly cash flow DataFrame.

        Returns:
            Populated FinancialStatements model.
        """
        # Income statement fields
        revenue = self._safe_get(financials, "Total Revenue", period_date, 0)
        net_profit = self._safe_get(financials, "Net Income", period_date, 0)
        gross_profit = self._safe_get(financials, "Gross Profit", period_date)

        # Calculate gross margin
        gross_margin = 0.0
        if gross_profit and revenue and float(revenue) != 0:
            gross_margin = float(gross_profit) / float(revenue)

        # Balance sheet fields
        total_assets = self._safe_get(
            balance_sheet, "Total Assets", period_date, 0
        )
        total_liabilities = self._safe_get(
            balance_sheet, "Total Liabilities Net Minority Interest", period_date
        )
        if total_liabilities is None:
            total_liabilities = self._safe_get(
                balance_sheet, "Total Liab", period_date, 0
            )

        stockholders_equity = self._safe_get(
            balance_sheet, "Stockholders Equity", period_date
        )
        if stockholders_equity is None:
            stockholders_equity = self._safe_get(
                balance_sheet, "Total Stockholder Equity", period_date
            )

        # ROE calculation
        roe = 0.0
        if stockholders_equity and float(stockholders_equity) != 0:
            roe = float(net_profit) / float(stockholders_equity)

        # Cash flow fields
        operating_cashflow = self._safe_get(
            cashflow, "Total Cash From Operating Activities", period_date
        )
        if operating_cashflow is None:
            operating_cashflow = self._safe_get(
                cashflow, "Operating Cash Flow", period_date, 0
            )

        # Shares outstanding for per-share metrics
        shares = self._safe_get(
            balance_sheet, "Share Issued", period_date
        )
        if shares is None:
            shares = self._safe_get(
                balance_sheet, "Ordinary Shares Number", period_date
            )

        # EPS
        eps = Decimal(0)
        if shares and float(shares) != 0:
            eps = Decimal(str(float(net_profit) / float(shares)))

        # BVPS (Book Value Per Share)
        bvps = Decimal(0)
        if stockholders_equity and shares and float(shares) != 0:
            bvps = Decimal(str(float(stockholders_equity) / float(shares)))

        # Convert period_date to date object
        if hasattr(period_date, "date"):
            period = period_date.date()
        else:
            period = date.fromisoformat(str(period_date)[:10])

        return FinancialStatements(
            ticker=ticker,
            period=period,
            market=Market.US,
            revenue=Decimal(str(float(revenue))),
            net_profit=Decimal(str(float(net_profit))),
            gross_margin=gross_margin,
            roe=roe,
            total_assets=Decimal(str(float(total_assets))),
            total_liabilities=Decimal(str(float(total_liabilities))),
            operating_cashflow=Decimal(str(float(operating_cashflow))),
            eps=eps,
            bvps=bvps,
            raw_data={
                "source": "yfinance",
                "ticker": ticker,
                "period": str(period),
            },
        )
