"""A-Share market data adapter using AKShare.

Implements the DataAdapter protocol for Chinese A-Share market data,
fetching financial statements, price history, key metrics, and macro
indicators via the akshare library.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd

from src.data.base import DataAdapter, DataCollectionError
from src.schemas import FinancialStatements, Market

logger = logging.getLogger(__name__)


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


class AShareAdapter:
    """DataAdapter implementation for Chinese A-Share market using AKShare.

    Handles ticker formats like "600519" (6-digit numeric codes) used by
    Shanghai and Shenzhen exchanges.
    """

    def get_financial_statements(
        self, ticker: str, periods: int = 4
    ) -> list[FinancialStatements]:
        """Fetch financial statements from Sina Finance via AKShare.

        Args:
            ticker: 6-digit A-share stock code (e.g., "600519" for Moutai).
            periods: Number of reporting periods to retrieve.

        Returns:
            List of FinancialStatements ordered from most recent to oldest.

        Raises:
            DataCollectionError: If data fetching or parsing fails.
        """
        import akshare as ak

        try:
            logger.info(f"Fetching financial statements for {ticker}, periods={periods}")

            # Fetch balance sheet for contract_liabilities and asset/liability data
            balance_df = ak.stock_financial_report_sina(
                stock=ticker, report_type="balance_sheet"
            )

            # Fetch income statement for revenue, net_profit, eps
            income_df = ak.stock_financial_report_sina(
                stock=ticker, report_type="income_statement"
            )

            # Fetch cash flow statement for operating_cashflow
            cashflow_df = ak.stock_financial_report_sina(
                stock=ticker, report_type="cash_flow"
            )

        except Exception as e:
            logger.error(f"Failed to fetch financial statements for {ticker}: {e}")
            raise DataCollectionError(
                f"Failed to fetch financial statements for {ticker}: {e}"
            ) from e

        try:
            results: list[FinancialStatements] = []

            # Determine available periods (columns represent reporting dates)
            # Sina financial reports have dates as columns (excluding the first
            # column which contains row labels)
            if balance_df.empty:
                logger.warning(f"Empty balance sheet data for {ticker}")
                return []

            # The first column is the item name; remaining columns are periods
            period_columns = balance_df.columns[1: 1 + periods]

            for col in period_columns:
                try:
                    period_date = pd.to_datetime(str(col)).date()
                except (ValueError, TypeError):
                    logger.warning(f"Cannot parse period date from column: {col}")
                    continue

                # Extract balance sheet items
                balance_data = _extract_column_as_dict(balance_df, col)
                income_data = _extract_column_as_dict(income_df, col)
                cashflow_data = _extract_column_as_dict(cashflow_df, col)

                revenue = _to_decimal(
                    _find_item(income_data, ["营业收入", "一、营业总收入", "营业总收入"])
                )
                net_profit = _to_decimal(
                    _find_item(income_data, ["净利润", "五、净利润", "归属于母公司所有者的净利润"])
                )
                total_assets = _to_decimal(
                    _find_item(balance_data, ["资产总计", "资产合计"])
                )
                total_liabilities = _to_decimal(
                    _find_item(balance_data, ["负债合计", "负债总计"])
                )
                contract_liabilities = _to_decimal(
                    _find_item(balance_data, ["合同负债"]),
                    default=Decimal("0"),
                )
                operating_cashflow = _to_decimal(
                    _find_item(
                        cashflow_data,
                        ["经营活动产生的现金流量净额", "经营活动现金流量净额"],
                    )
                )

                # Calculate derived metrics
                equity = total_assets - total_liabilities
                gross_margin = _calculate_gross_margin(income_data)
                roe = (
                    float(net_profit / equity) if equity != 0 else 0.0
                )

                # EPS and BVPS - try to find directly or default to 0
                eps = _to_decimal(
                    _find_item(income_data, ["基本每股收益", "每股收益"])
                )
                bvps = _to_decimal(
                    _find_item(balance_data, ["每股净资产"])
                )

                stmt = FinancialStatements(
                    ticker=ticker,
                    period=period_date,
                    market=Market.A_SHARE,
                    revenue=revenue,
                    net_profit=net_profit,
                    gross_margin=gross_margin,
                    roe=roe,
                    contract_liabilities=contract_liabilities if contract_liabilities != 0 else None,
                    total_assets=total_assets,
                    total_liabilities=total_liabilities,
                    operating_cashflow=operating_cashflow,
                    eps=eps,
                    bvps=bvps,
                    raw_data={
                        "balance": {k: str(v) for k, v in balance_data.items()},
                        "income": {k: str(v) for k, v in income_data.items()},
                        "cashflow": {k: str(v) for k, v in cashflow_data.items()},
                    },
                )
                results.append(stmt)

            logger.info(f"Successfully parsed {len(results)} periods for {ticker}")
            return results

        except DataCollectionError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse financial statements for {ticker}: {e}")
            raise DataCollectionError(
                f"Failed to parse financial statements for {ticker}: {e}"
            ) from e

    def get_price_history(
        self, ticker: str, start: date, end: date
    ) -> pd.DataFrame:
        """Fetch daily price history with forward-adjusted prices.

        Args:
            ticker: 6-digit A-share stock code (e.g., "600519").
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            DataFrame with columns: date, open, high, low, close, volume.

        Raises:
            DataCollectionError: If data fetching fails.
        """
        import akshare as ak

        try:
            logger.info(
                f"Fetching price history for {ticker} from {start} to {end}"
            )
            df = ak.stock_zh_a_hist(
                symbol=ticker,
                period="daily",
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                adjust="qfq",
            )
        except Exception as e:
            logger.error(f"Failed to fetch price history for {ticker}: {e}")
            raise DataCollectionError(
                f"Failed to fetch price history for {ticker}: {e}"
            ) from e

        try:
            if df.empty:
                logger.warning(f"No price data returned for {ticker}")
                return pd.DataFrame(
                    columns=["date", "open", "high", "low", "close", "volume"]
                )

            # AKShare returns columns in Chinese; map to English
            column_map = {
                "日期": "date",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
            }

            # Use the mapping for known columns, fall back to lowercase English
            # names if the dataframe already uses them
            if "日期" in df.columns:
                df = df.rename(columns=column_map)
            else:
                # Already English column names (newer akshare versions)
                df.columns = df.columns.str.lower()

            # Select and order the required columns
            required_cols = ["date", "open", "high", "low", "close", "volume"]
            available = [c for c in required_cols if c in df.columns]
            df = df[available].copy()

            # Ensure date column is proper datetime then date
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"]).dt.date

            df = df.sort_values("date").reset_index(drop=True)
            logger.info(f"Returned {len(df)} price records for {ticker}")
            return df

        except DataCollectionError:
            raise
        except Exception as e:
            logger.error(f"Failed to process price data for {ticker}: {e}")
            raise DataCollectionError(
                f"Failed to process price data for {ticker}: {e}"
            ) from e

    def get_key_metrics(self, ticker: str) -> dict[str, float]:
        """Fetch key financial metrics for an A-share stock.

        Args:
            ticker: 6-digit A-share stock code (e.g., "600519").

        Returns:
            Dict with keys: pe, pb, ps, market_cap, dividend_yield
            (where available).

        Raises:
            DataCollectionError: If data fetching fails.
        """
        import akshare as ak

        try:
            logger.info(f"Fetching key metrics for {ticker}")
            df = ak.stock_individual_info_em(symbol=ticker)
        except Exception as e:
            logger.error(f"Failed to fetch key metrics for {ticker}: {e}")
            raise DataCollectionError(
                f"Failed to fetch key metrics for {ticker}: {e}"
            ) from e

        try:
            metrics: dict[str, float] = {}

            if df.empty:
                logger.warning(f"No metrics data returned for {ticker}")
                return metrics

            # stock_individual_info_em returns a 2-column DataFrame:
            # column 0: item name, column 1: item value
            # Convert to a lookup dict
            info_dict: dict[str, str] = {}
            for _, row in df.iterrows():
                key = str(row.iloc[0]).strip()
                val = row.iloc[1]
                info_dict[key] = val

            # Map Chinese field names to our metric keys
            metric_mapping = {
                "pe": ["市盈率-动态", "市盈率(动态)", "市盈率"],
                "pb": ["市净率", "市净率(MRQ)"],
                "ps": ["市销率", "市销率(TTM)"],
                "market_cap": ["总市值"],
                "dividend_yield": ["股息率", "股息率(%)"],
            }

            for metric_key, possible_names in metric_mapping.items():
                for name in possible_names:
                    if name in info_dict:
                        value = _to_float(info_dict[name], default=None)
                        if value is not None:
                            # Convert market_cap from yuan to 亿 for readability
                            if metric_key == "market_cap":
                                metrics[metric_key] = value
                            else:
                                metrics[metric_key] = value
                            break

            logger.info(f"Retrieved metrics for {ticker}: {list(metrics.keys())}")
            return metrics

        except DataCollectionError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse key metrics for {ticker}: {e}")
            raise DataCollectionError(
                f"Failed to parse key metrics for {ticker}: {e}"
            ) from e

    def get_macro_indicators(self) -> dict[str, pd.Series]:
        """Fetch Chinese macro indicators: CPI, PMI, M2, social financing.

        Returns:
            Dict with keys: cpi, pmi, m2, social_financing, each mapping
            to a pandas Series indexed by date.

        Raises:
            DataCollectionError: If data fetching fails.
        """
        import akshare as ak

        indicators: dict[str, pd.Series] = {}

        # CPI
        try:
            logger.info("Fetching CPI data")
            cpi_df = ak.macro_china_cpi()
            if not cpi_df.empty:
                # Try to build a date-indexed series
                date_col = _find_date_column(cpi_df)
                value_col = _find_value_column(cpi_df, exclude=date_col)
                if date_col and value_col:
                    series = pd.Series(
                        cpi_df[value_col].values,
                        index=pd.to_datetime(cpi_df[date_col]),
                        name="cpi",
                    )
                    indicators["cpi"] = series.dropna()
        except Exception as e:
            logger.warning(f"Failed to fetch CPI data: {e}")

        # PMI
        try:
            logger.info("Fetching PMI data")
            pmi_df = ak.macro_china_pmi()
            if not pmi_df.empty:
                date_col = _find_date_column(pmi_df)
                value_col = _find_value_column(pmi_df, exclude=date_col)
                if date_col and value_col:
                    series = pd.Series(
                        pmi_df[value_col].values,
                        index=pd.to_datetime(pmi_df[date_col]),
                        name="pmi",
                    )
                    indicators["pmi"] = series.dropna()
        except Exception as e:
            logger.warning(f"Failed to fetch PMI data: {e}")

        # M2
        try:
            logger.info("Fetching M2 data")
            m2_df = ak.macro_china_m2()
            if not m2_df.empty:
                date_col = _find_date_column(m2_df)
                value_col = _find_value_column(m2_df, exclude=date_col)
                if date_col and value_col:
                    series = pd.Series(
                        m2_df[value_col].values,
                        index=pd.to_datetime(m2_df[date_col]),
                        name="m2",
                    )
                    indicators["m2"] = series.dropna()
        except Exception as e:
            logger.warning(f"Failed to fetch M2 data: {e}")

        # Social Financing
        try:
            logger.info("Fetching social financing data")
            sf_df = ak.macro_china_shrzgm()
            if not sf_df.empty:
                date_col = _find_date_column(sf_df)
                value_col = _find_value_column(sf_df, exclude=date_col)
                if date_col and value_col:
                    series = pd.Series(
                        sf_df[value_col].values,
                        index=pd.to_datetime(sf_df[date_col]),
                        name="social_financing",
                    )
                    indicators["social_financing"] = series.dropna()
        except Exception as e:
            logger.warning(f"Failed to fetch social financing data: {e}")

        if not indicators:
            logger.error("Failed to fetch any macro indicators")
            raise DataCollectionError(
                "Failed to fetch any macro indicators from AKShare"
            )

        logger.info(f"Retrieved macro indicators: {list(indicators.keys())}")
        return indicators


# --- Helper Functions ---


def _extract_column_as_dict(df: pd.DataFrame, col) -> dict:
    """Extract a single period column from a Sina financial report DataFrame.

    The first column contains item names; the target column contains values.
    Returns a dict mapping item name -> value.
    """
    if df.empty or col not in df.columns:
        return {}

    label_col = df.columns[0]
    result = {}
    for _, row in df.iterrows():
        key = str(row[label_col]).strip() if pd.notna(row[label_col]) else ""
        if key:
            result[key] = row[col]
    return result


def _find_item(data: dict, possible_keys: list[str]):
    """Find the first matching key in a dict, return its value or None."""
    for key in possible_keys:
        if key in data:
            val = data[key]
            if val is not None and not (isinstance(val, float) and pd.isna(val)):
                return val
    return None


def _calculate_gross_margin(income_data: dict) -> float:
    """Calculate gross margin from income statement data."""
    revenue = _to_float(
        _find_item(income_data, ["营业收入", "一、营业总收入", "营业总收入"])
    )
    cost = _to_float(
        _find_item(income_data, ["营业成本", "二、营业总成本", "营业总成本"])
    )
    if revenue == 0:
        return 0.0
    return (revenue - cost) / revenue


def _find_date_column(df: pd.DataFrame) -> str | None:
    """Heuristically find the date column in a macro indicator DataFrame."""
    for col in df.columns:
        col_lower = str(col).lower()
        if any(kw in col_lower for kw in ["date", "日期", "月份", "时间", "统计时间"]):
            return col
    # Fall back to first column if it looks like dates
    first_col = df.columns[0]
    try:
        pd.to_datetime(df[first_col].head(3))
        return first_col
    except (ValueError, TypeError):
        return None


def _find_value_column(df: pd.DataFrame, exclude: str | None = None) -> str | None:
    """Heuristically find the primary numeric value column."""
    for col in df.columns:
        if col == exclude:
            continue
        col_lower = str(col).lower()
        if any(
            kw in col_lower
            for kw in [
                "同比", "全国", "国房", "数值", "value", "当月",
                "制造业", "cpi", "pmi", "m2",
            ]
        ):
            return col
    # Fall back to second column (first numeric-looking one after date)
    for col in df.columns:
        if col == exclude:
            continue
        if df[col].dtype in ("float64", "int64", "float32", "int32"):
            return col
    # Last resort: first column that isn't the date
    for col in df.columns:
        if col != exclude:
            return col
    return None
