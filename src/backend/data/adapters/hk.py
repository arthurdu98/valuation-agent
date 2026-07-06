"""Hong Kong market data adapter using AKShare.

Uses stock_financial_hk_analysis_indicator_em for core financial metrics
and stock_hk_hist for price history.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pandas as pd

from src.backend.data.base import DataCollectionError
from src.backend.schemas import FinancialStatements, Market

logger = logging.getLogger(__name__)


def _to_decimal(value, default: Decimal = Decimal("0")) -> Decimal:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _to_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        result = float(value)
        return default if pd.isna(result) else result
    except (ValueError, TypeError):
        return default


def _pad_hk(ticker: str) -> str:
    """Normalise to 5-digit zero-padded code, e.g. '9992' → '09992'."""
    return ticker.strip().lstrip("0").zfill(5) if ticker.strip().isdigit() else ticker.strip()


class HKAdapter:
    """DataAdapter for Hong Kong Stock Exchange via AKShare.

    Primary interface: stock_financial_hk_analysis_indicator_em
    Returns one row per annual reporting period with standardised fields.
    """

    def get_financial_statements(
        self, ticker: str, periods: int = 4
    ) -> list[FinancialStatements]:
        import akshare as ak

        symbol = _pad_hk(ticker)
        try:
            logger.info(f"Fetching HK financials for {symbol}, periods={periods}")
            df = ak.stock_financial_hk_analysis_indicator_em(
                symbol=symbol, indicator="年度"
            )
        except Exception as e:
            raise DataCollectionError(
                f"AKShare HK fetch failed for {ticker}: {e}"
            ) from e

        if df is None or df.empty:
            raise DataCollectionError(f"No HK financial data returned for {ticker}")

        df = df.head(periods)
        results: list[FinancialStatements] = []

        for _, row in df.iterrows():
            try:
                period_raw = row.get("REPORT_DATE", "")
                if pd.isna(period_raw):
                    continue
                period_date = pd.to_datetime(period_raw).date()

                revenue        = _to_decimal(row.get("OPERATE_INCOME"))
                net_profit     = _to_decimal(row.get("HOLDER_PROFIT"))
                gross_margin   = _to_float(row.get("GROSS_PROFIT_RATIO"))
                roe            = _to_float(row.get("ROE_AVG"))
                total_assets   = _to_decimal(None)   # not in this interface
                total_liab     = _to_decimal(None)
                ocf_per_share  = _to_float(row.get("PER_NETCASH_OPERATE"))
                eps            = _to_decimal(row.get("BASIC_EPS"))
                bvps           = _to_decimal(row.get("BPS"))
                debt_ratio     = _to_float(row.get("DEBT_ASSET_RATIO")) / 100.0

                # Approximate total assets from revenue + debt ratio when not available
                if revenue and revenue > 0 and debt_ratio < 1.0:
                    # We can't infer assets without more data; leave as 0
                    pass

                results.append(FinancialStatements(
                    ticker=ticker,
                    period=period_date,
                    market=Market.HK,
                    revenue=revenue,
                    net_profit=net_profit,
                    gross_margin=gross_margin,
                    roe=roe,
                    contract_liabilities=None,
                    total_assets=total_assets if total_assets else Decimal("0"),
                    total_liabilities=total_liab if total_liab else Decimal("0"),
                    operating_cashflow=_to_decimal(ocf_per_share),  # per-share proxy
                    eps=eps,
                    bvps=bvps,
                    raw_data=row.to_dict(),
                    fetched_at=datetime.now(),
                ))
            except Exception as e:
                logger.warning(f"Skip HK row for {ticker}: {e}")
                continue

        logger.info(f"Parsed {len(results)} HK periods for {ticker}")
        return results

    def get_price_history(
        self, ticker: str, start: date, end: date
    ) -> pd.DataFrame:
        import akshare as ak

        symbol = _pad_hk(ticker)
        try:
            df = ak.stock_hk_hist(
                symbol=symbol,
                period="daily",
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                adjust="qfq",
            )
        except Exception as e:
            raise DataCollectionError(
                f"HK price history fetch failed for {ticker}: {e}"
            ) from e

        if df is None or df.empty:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

        col_map = {"日期": "date", "开盘": "open", "最高": "high",
                   "最低": "low", "收盘": "close", "成交量": "volume"}
        df = df.rename(columns=col_map)
        cols = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in df.columns]
        df = df[cols].copy()
        df["date"] = pd.to_datetime(df["date"]).dt.date
        return df.sort_values("date").reset_index(drop=True)

    def get_key_metrics(self, ticker: str) -> dict[str, float]:
        import akshare as ak

        symbol = _pad_hk(ticker)
        try:
            df = ak.stock_financial_hk_analysis_indicator_em(
                symbol=symbol, indicator="年度"
            )
            if df is None or df.empty:
                return {}
            row = df.iloc[0]
            return {
                "gross_margin":    _to_float(row.get("GROSS_PROFIT_RATIO")),
                "roe":             _to_float(row.get("ROE_AVG")),
                "net_margin":      _to_float(row.get("NET_PROFIT_RATIO")),
                "revenue_growth":  _to_float(row.get("OPERATE_INCOME_YOY")),
                "debt_ratio":      _to_float(row.get("DEBT_ASSET_RATIO")),
                "current_ratio":   _to_float(row.get("CURRENT_RATIO")),
                "eps":             _to_float(row.get("BASIC_EPS")),
            }
        except Exception as e:
            raise DataCollectionError(f"HK key metrics failed for {ticker}: {e}") from e

    def get_macro_indicators(self) -> dict[str, pd.Series]:
        return {}
