"""Hong Kong market data adapter using AKShare.

Provides access to HK-listed stock data including financial statements,
price history, and key metrics via AKShare's Hong Kong interfaces.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import akshare as ak
import pandas as pd

from src.data.base import DataCollectionError
from src.schemas import FinancialStatements, Market

logger = logging.getLogger(__name__)


class HKAdapter:
    """Data adapter for Hong Kong Stock Exchange (HKEX) via AKShare.

    Satisfies the DataAdapter protocol defined in src.data.base.

    Ticker format: 5-digit zero-padded string, e.g. "09992" for Pop Mart,
    "00700" for Tencent, "09988" for Alibaba.
    """

    def get_financial_statements(
        self, ticker: str, periods: int = 4
    ) -> list[FinancialStatements]:
        """Fetch financial statements for an HK-listed stock.

        Args:
            ticker: HK stock code, e.g. "09992".
            periods: Number of reporting periods to retrieve (default 4).
                     HK stocks typically report semi-annually (interim + annual).

        Returns:
            List of FinancialStatements ordered from most recent to oldest.

        Raises:
            DataCollectionError: If data cannot be fetched or parsed.
        """
        try:
            # TODO: Verify ak.stock_financial_hk_report_em interface availability
            # and exact parameter names. AKShare HK financial interfaces may change.
            # Possible alternatives:
            #   - ak.stock_financial_report_sina (older interface)
            #   - ak.stock_hk_financial_report
            #   - Manual scraping fallback
            symbol = ticker.lstrip("0") if ticker.startswith("0") else ticker
            symbol_padded = ticker.zfill(5)

            # Try to fetch income statement data
            # TODO: ak.stock_financial_hk may require symbol format like "09992"
            # or "HK09992". Verify against actual AKShare version.
            try:
                df_income = ak.stock_financial_analysis_indicator_em(
                    symbol=f"HK{symbol_padded}"
                )
            except Exception:
                logger.warning(
                    f"Failed to get HK financial data via EM interface for {ticker}, "
                    "trying alternative interface"
                )
                # TODO: Try alternative AKShare HK financial interfaces
                # ak.stock_hk_financial_report or similar
                raise DataCollectionError(
                    f"No available financial data interface for HK stock {ticker}. "
                    "AKShare HK financial interfaces may be limited or require "
                    "different symbol formats."
                )

            if df_income is None or df_income.empty:
                raise DataCollectionError(
                    f"No financial data returned for HK stock {ticker}"
                )

            # Limit to requested periods
            df_income = df_income.head(periods)

            results: list[FinancialStatements] = []
            for _, row in df_income.iterrows():
                try:
                    # TODO: Column names depend on the actual AKShare interface.
                    # These mappings need verification against real API responses.
                    period_date = _parse_period_date(row)
                    fs = FinancialStatements(
                        ticker=ticker,
                        period=period_date,
                        market=Market.HK,
                        revenue=Decimal(str(row.get("营业收入", 0) or 0)),
                        net_profit=Decimal(str(row.get("净利润", 0) or 0)),
                        gross_margin=float(row.get("毛利率", 0) or 0),
                        roe=float(row.get("净资产收益率", 0) or 0),
                        contract_liabilities=None,  # Not typically available for HK
                        total_assets=Decimal(str(row.get("总资产", 0) or 0)),
                        total_liabilities=Decimal(str(row.get("总负债", 0) or 0)),
                        operating_cashflow=Decimal(
                            str(row.get("经营活动产生的现金流量净额", 0) or 0)
                        ),
                        eps=Decimal(str(row.get("基本每股收益", 0) or 0)),
                        bvps=Decimal(str(row.get("每股净资产", 0) or 0)),
                        raw_data=row.to_dict() if hasattr(row, "to_dict") else {},
                        fetched_at=datetime.now(),
                    )
                    results.append(fs)
                except (KeyError, TypeError, ValueError) as e:
                    logger.warning(
                        f"Skipping malformed row for {ticker}: {e}"
                    )
                    continue

            if not results:
                raise DataCollectionError(
                    f"Could not parse any financial statements for HK stock {ticker}"
                )

            return results

        except DataCollectionError:
            raise
        except Exception as e:
            raise DataCollectionError(
                f"Failed to fetch financial statements for HK stock {ticker}: {e}"
            ) from e

    def get_price_history(
        self, ticker: str, start: date, end: date
    ) -> pd.DataFrame:
        """Fetch daily price history for an HK-listed stock.

        Uses ak.stock_hk_hist with forward-adjusted prices (qfq).

        Args:
            ticker: HK stock code, e.g. "09992".
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            DataFrame with columns: date, open, high, low, close, volume.

        Raises:
            DataCollectionError: If data cannot be fetched or parsed.
        """
        try:
            symbol = ticker.zfill(5)
            start_str = start.strftime("%Y%m%d")
            end_str = end.strftime("%Y%m%d")

            # TODO: Verify ak.stock_hk_hist parameter names and symbol format.
            # Some versions use symbol="09992", others may need "hk09992".
            df = ak.stock_hk_hist(
                symbol=symbol,
                period="daily",
                start_date=start_str,
                end_date=end_str,
                adjust="qfq",
            )

            if df is None or df.empty:
                raise DataCollectionError(
                    f"No price history returned for HK stock {ticker} "
                    f"between {start} and {end}"
                )

            # Normalize column names to standard format
            # TODO: Verify actual column names returned by ak.stock_hk_hist
            column_map = {
                "日期": "date",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
            }
            df = df.rename(columns=column_map)

            # Ensure we have the required columns
            required_cols = ["date", "open", "high", "low", "close", "volume"]
            # If Chinese column names weren't present, try English
            if not all(col in df.columns for col in required_cols):
                english_map = {
                    "Date": "date",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                }
                df = df.rename(columns=english_map)

            # Select and order standard columns
            available_cols = [c for c in required_cols if c in df.columns]
            df = df[available_cols]

            # Sort by date ascending
            if "date" in df.columns:
                df = df.sort_values("date").reset_index(drop=True)

            return df

        except DataCollectionError:
            raise
        except Exception as e:
            raise DataCollectionError(
                f"Failed to fetch price history for HK stock {ticker}: {e}"
            ) from e

    def get_key_metrics(self, ticker: str) -> dict[str, float]:
        """Fetch key financial metrics for an HK-listed stock.

        Attempts to retrieve PE, PB, and market cap from AKShare's
        HK spot data interface.

        Args:
            ticker: HK stock code, e.g. "09992".

        Returns:
            Dictionary with keys like 'pe', 'pb', 'market_cap'.

        Raises:
            DataCollectionError: If data cannot be fetched or parsed.
        """
        try:
            # TODO: Verify ak.stock_hk_spot_em() returns all HK stocks
            # and confirm column names for PE, PB, market cap.
            df = ak.stock_hk_spot_em()

            if df is None or df.empty:
                raise DataCollectionError(
                    "Failed to fetch HK spot data from AKShare"
                )

            symbol = ticker.zfill(5)

            # TODO: Verify the code column name. Could be "代码", "symbol", etc.
            # Filter for our specific ticker
            mask = df["代码"].astype(str).str.zfill(5) == symbol
            if not mask.any():
                # Try alternative column name
                for col_name in ["代码", "symbol", "code", "股票代码"]:
                    if col_name in df.columns:
                        mask = df[col_name].astype(str).str.zfill(5) == symbol
                        if mask.any():
                            break

            if not mask.any():
                raise DataCollectionError(
                    f"Ticker {ticker} not found in HK spot data"
                )

            row = df[mask].iloc[0]
            metrics: dict[str, float] = {}

            # TODO: Column names need verification against actual AKShare output.
            # Map Chinese column names to metric keys
            metric_columns = {
                "pe": ["市盈率", "PE", "pe_ratio"],
                "pb": ["市净率", "PB", "pb_ratio"],
                "market_cap": ["总市值", "market_cap", "MarketCap"],
            }

            for metric_key, possible_cols in metric_columns.items():
                for col in possible_cols:
                    if col in row.index:
                        val = row[col]
                        if pd.notna(val):
                            try:
                                metrics[metric_key] = float(val)
                            except (ValueError, TypeError):
                                pass
                        break

            if not metrics:
                raise DataCollectionError(
                    f"No key metrics could be extracted for HK stock {ticker}"
                )

            return metrics

        except DataCollectionError:
            raise
        except Exception as e:
            raise DataCollectionError(
                f"Failed to fetch key metrics for HK stock {ticker}: {e}"
            ) from e

    def get_macro_indicators(self) -> dict[str, pd.Series]:
        """Return macro indicators relevant to the Hong Kong market.

        HK macro indicators largely follow China and US macro environments,
        which are handled by their respective adapters. Returns an empty dict.

        Returns:
            Empty dictionary. HK-specific macro data is limited in AKShare;
            use China (A-share) and US adapters for macro context.
        """
        # HK follows China/US macro environments.
        # Relevant indicators (HIBOR, HSI components, HK CPI) are not
        # well-covered by AKShare. Delegate to CN/US adapters for macro context.
        return {}


def _parse_period_date(row: Any) -> date:
    """Extract reporting period date from a financial data row.

    Args:
        row: A pandas Series or dict-like object from financial data.

    Returns:
        The parsed date representing the reporting period.

    Raises:
        DataCollectionError: If no date field can be parsed.
    """
    # TODO: Adapt to actual column names from AKShare HK financial interfaces
    date_columns = ["报告期", "日期", "date", "report_date", "period"]

    for col in date_columns:
        if col in row.index if hasattr(row, "index") else col in row:
            val = row[col] if hasattr(row, "__getitem__") else getattr(row, col)
            if val is None:
                continue
            if isinstance(val, (date, datetime)):
                return val if isinstance(val, date) else val.date()
            try:
                return pd.to_datetime(str(val)).date()
            except (ValueError, TypeError):
                continue

    raise DataCollectionError(
        "Could not parse reporting period date from financial data row"
    )
