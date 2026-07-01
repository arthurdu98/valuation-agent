"""A-Share market data adapter using Tushare Pro API.

Backup adapter implementing the DataAdapter protocol for Chinese A-Share
market data via the Tushare Pro library. Used as a fallback when the
primary AKShare adapter is unavailable or rate-limited.
"""

from __future__ import annotations

import logging
import time
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd

from src.config import settings
from src.data.base import DataAdapter, DataCollectionError
from src.schemas import FinancialStatements, Market

logger = logging.getLogger(__name__)


def _to_ts_code(ticker: str) -> str:
    """Convert a plain 6-digit ticker to Tushare ts_code format.

    Tushare uses the format "600519.SH" (Shanghai) or "000858.SZ" (Shenzhen).
    Shanghai codes start with 6; Shenzhen codes start with 0 or 3.

    Args:
        ticker: Plain 6-digit stock code (e.g., "600519").

    Returns:
        Tushare-formatted ts_code (e.g., "600519.SH").
    """
    ticker = ticker.strip()
    # Remove any existing suffix
    if "." in ticker:
        return ticker.upper()
    if ticker.startswith("6"):
        return f"{ticker}.SH"
    else:
        return f"{ticker}.SZ"


def _to_decimal(value, default: Decimal = Decimal("0")) -> Decimal:
    """Safely convert a value to Decimal, returning default on failure."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _to_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    if value is None:
        return default
    try:
        result = float(value)
        if pd.isna(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


class TushareAdapter:
    """DataAdapter implementation for Chinese A-Share market using Tushare Pro.

    Requires a valid Tushare Pro token configured in settings.tushare_token.
    Handles rate limiting with built-in sleep delays between API calls.
    Token validation is deferred to first actual API call (lazy init).
    """

    def __init__(self) -> None:
        """Initialize adapter. Token is validated lazily on first API call."""
        self._pro = None
        self._rate_limit_delay = 0.3  # seconds between API calls

    def _ensure_connected(self) -> None:
        """Lazy-initialize Tushare Pro API connection."""
        if self._pro is not None:
            return
        import tushare as ts
        token = settings.tushare_token
        if not token:
            raise DataCollectionError(
                "Tushare token not configured. Set TUSHARE_TOKEN in .env file."
            )
        ts.set_token(token)
        self._pro = ts.pro_api(token)

    def _sleep(self) -> None:
        """Sleep to respect Tushare rate limits."""
        time.sleep(self._rate_limit_delay)

    def get_financial_statements(
        self, ticker: str, periods: int = 4
    ) -> list[FinancialStatements]:
        """Fetch financial statements from Tushare Pro.

        Uses balancesheet, income, and cashflow interfaces to assemble
        complete financial statement records.

        Args:
            ticker: 6-digit A-share stock code (e.g., "600519").
            periods: Number of reporting periods to retrieve.

        Returns:
            List of FinancialStatements ordered from most recent to oldest.

        Raises:
            DataCollectionError: If data fetching or parsing fails.
        """
        self._ensure_connected()
        ts_code = _to_ts_code(ticker)

        try:
            logger.info(
                f"Fetching financial statements for {ts_code} via Tushare, "
                f"periods={periods}"
            )

            # Fetch balance sheet
            balance_df = self._pro.balancesheet(
                ts_code=ts_code, limit=periods
            )
            self._sleep()

            # Fetch income statement
            income_df = self._pro.income(
                ts_code=ts_code, limit=periods
            )
            self._sleep()

            # Fetch cash flow statement
            cashflow_df = self._pro.cashflow(
                ts_code=ts_code, limit=periods
            )
            self._sleep()

        except Exception as e:
            logger.error(
                f"Failed to fetch financial statements for {ts_code}: {e}"
            )
            raise DataCollectionError(
                f"Failed to fetch financial statements for {ts_code}: {e}"
            ) from e

        try:
            results: list[FinancialStatements] = []

            if balance_df is None or balance_df.empty:
                logger.warning(f"Empty balance sheet data for {ts_code}")
                return []

            # Tushare returns end_date as the reporting period (e.g., "20231231")
            for idx in range(min(periods, len(balance_df))):
                balance_row = balance_df.iloc[idx] if idx < len(balance_df) else None
                income_row = income_df.iloc[idx] if income_df is not None and idx < len(income_df) else None
                cashflow_row = cashflow_df.iloc[idx] if cashflow_df is not None and idx < len(cashflow_df) else None

                if balance_row is None:
                    continue

                # Parse period date from end_date field
                end_date_str = str(balance_row.get("end_date", ""))
                try:
                    period_date = pd.to_datetime(end_date_str).date()
                except (ValueError, TypeError):
                    logger.warning(f"Cannot parse period date: {end_date_str}")
                    continue

                # Extract values from balance sheet
                total_assets = _to_decimal(balance_row.get("total_assets"))
                total_liabilities = _to_decimal(balance_row.get("total_liab"))
                contract_liabilities = _to_decimal(
                    balance_row.get("contract_liab"), default=Decimal("0")
                )

                # Extract values from income statement
                revenue = Decimal("0")
                net_profit = Decimal("0")
                eps = Decimal("0")
                gross_margin = 0.0

                if income_row is not None:
                    revenue = _to_decimal(income_row.get("revenue"))
                    net_profit = _to_decimal(income_row.get("n_income"))
                    eps = _to_decimal(income_row.get("basic_eps"))

                    # Calculate gross margin
                    rev_float = _to_float(income_row.get("revenue"))
                    oper_cost = _to_float(income_row.get("oper_cost"))
                    if rev_float > 0:
                        gross_margin = (rev_float - oper_cost) / rev_float

                # Extract operating cash flow
                operating_cashflow = Decimal("0")
                if cashflow_row is not None:
                    operating_cashflow = _to_decimal(
                        cashflow_row.get("n_cashflow_act")
                    )

                # Calculate ROE
                equity = total_assets - total_liabilities
                roe = float(net_profit / equity) if equity != 0 else 0.0

                # BVPS from balance sheet
                bvps = Decimal("0")
                if equity > 0:
                    total_share = _to_float(balance_row.get("total_share"))
                    if total_share > 0:
                        bvps = Decimal(str(float(equity) / total_share))

                stmt = FinancialStatements(
                    ticker=ticker,
                    period=period_date,
                    market=Market.A_SHARE,
                    revenue=revenue,
                    net_profit=net_profit,
                    gross_margin=gross_margin,
                    roe=roe,
                    contract_liabilities=(
                        contract_liabilities if contract_liabilities != 0 else None
                    ),
                    total_assets=total_assets,
                    total_liabilities=total_liabilities,
                    operating_cashflow=operating_cashflow,
                    eps=eps,
                    bvps=bvps,
                    raw_data={
                        "source": "tushare",
                        "ts_code": ts_code,
                        "end_date": end_date_str,
                    },
                )
                results.append(stmt)

            logger.info(
                f"Successfully parsed {len(results)} periods for {ts_code}"
            )
            return results

        except DataCollectionError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to parse financial statements for {ts_code}: {e}"
            )
            raise DataCollectionError(
                f"Failed to parse financial statements for {ts_code}: {e}"
            ) from e

    def get_price_history(
        self, ticker: str, start: date, end: date
    ) -> pd.DataFrame:
        """Fetch daily price history from Tushare Pro.

        Args:
            ticker: 6-digit A-share stock code (e.g., "600519").
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            DataFrame with columns: date, open, high, low, close, volume.

        Raises:
            DataCollectionError: If data fetching fails.
        """
        self._ensure_connected()
        ts_code = _to_ts_code(ticker)

        try:
            logger.info(
                f"Fetching price history for {ts_code} from {start} to {end}"
            )
            df = self._pro.daily(
                ts_code=ts_code,
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
            )
            self._sleep()
        except Exception as e:
            logger.error(f"Failed to fetch price history for {ts_code}: {e}")
            raise DataCollectionError(
                f"Failed to fetch price history for {ts_code}: {e}"
            ) from e

        try:
            if df is None or df.empty:
                logger.warning(f"No price data returned for {ts_code}")
                return pd.DataFrame(
                    columns=["date", "open", "high", "low", "close", "volume"]
                )

            # Tushare daily returns: ts_code, trade_date, open, high, low,
            # close, pre_close, change, pct_chg, vol, amount
            df = df.rename(columns={
                "trade_date": "date",
                "vol": "volume",
            })

            # Convert trade_date from "YYYYMMDD" string to date
            df["date"] = pd.to_datetime(df["date"]).dt.date

            # Select required columns
            required_cols = ["date", "open", "high", "low", "close", "volume"]
            available = [c for c in required_cols if c in df.columns]
            df = df[available].copy()

            # Sort ascending by date (Tushare returns descending)
            df = df.sort_values("date").reset_index(drop=True)

            logger.info(f"Returned {len(df)} price records for {ts_code}")
            return df

        except DataCollectionError:
            raise
        except Exception as e:
            logger.error(f"Failed to process price data for {ts_code}: {e}")
            raise DataCollectionError(
                f"Failed to process price data for {ts_code}: {e}"
            ) from e

    def get_key_metrics(self, ticker: str) -> dict[str, float]:
        """Fetch key financial metrics from Tushare daily_basic.

        Args:
            ticker: 6-digit A-share stock code (e.g., "600519").

        Returns:
            Dict with keys: pe, pb, ps, market_cap, dividend_yield, etc.

        Raises:
            DataCollectionError: If data fetching fails.
        """
        self._ensure_connected()
        ts_code = _to_ts_code(ticker)

        try:
            logger.info(f"Fetching key metrics for {ts_code} via Tushare")
            df = self._pro.daily_basic(
                ts_code=ts_code, limit=1
            )
            self._sleep()
        except Exception as e:
            logger.error(f"Failed to fetch key metrics for {ts_code}: {e}")
            raise DataCollectionError(
                f"Failed to fetch key metrics for {ts_code}: {e}"
            ) from e

        try:
            metrics: dict[str, float] = {}

            if df is None or df.empty:
                logger.warning(f"No metrics data returned for {ts_code}")
                return metrics

            row = df.iloc[0]

            # Map Tushare daily_basic fields to our standard metric keys
            field_mapping = {
                "pe": "pe_ttm",
                "pb": "pb",
                "ps": "ps_ttm",
                "market_cap": "total_mv",
                "dividend_yield": "dv_ttm",
                "turnover_rate": "turnover_rate",
                "total_share": "total_share",
                "float_share": "float_share",
            }

            for metric_key, tushare_field in field_mapping.items():
                value = _to_float(row.get(tushare_field), default=None)
                if value is not None:
                    metrics[metric_key] = value

            logger.info(
                f"Retrieved metrics for {ts_code}: {list(metrics.keys())}"
            )
            return metrics

        except DataCollectionError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse key metrics for {ts_code}: {e}")
            raise DataCollectionError(
                f"Failed to parse key metrics for {ts_code}: {e}"
            ) from e

    def get_macro_indicators(self) -> dict[str, pd.Series]:
        """Return empty dict — macro indicators handled by AKShare primary.

        The AKShare adapter is the primary source for Chinese macro data.
        This method exists to satisfy the DataAdapter protocol.

        Returns:
            Empty dictionary.
        """
        logger.debug(
            "TushareAdapter.get_macro_indicators called — "
            "macro data handled by primary AKShare adapter"
        )
        return {}
