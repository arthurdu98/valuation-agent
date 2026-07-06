"""A-Share market data adapter using AKShare.

Implements the DataAdapter protocol for Chinese A-Share market data.
AKShare >= 1.12 changed stock_financial_report_sina: each ROW is now a
reporting period (column '报告日'), and field names are the column headers.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd

from src.backend.data.base import DataAdapter, DataCollectionError
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


def _find_col(row: pd.Series, candidates: list[str]) -> float | None:
    """Return the first non-null value among candidate column names."""
    for name in candidates:
        if name in row.index and not pd.isna(row[name]):
            return row[name]
    return None


def _ticker_to_sina(ticker: str) -> str:
    """Convert '600519' → 'sh600519', '000858' → 'sz000858'."""
    ticker = ticker.strip()
    if ticker.startswith(("sh", "sz")):
        return ticker
    if ticker.startswith("6"):
        return f"sh{ticker}"
    return f"sz{ticker}"


def _calculate_gross_margin(row: pd.Series) -> float:
    """Compute gross margin from income statement row."""
    revenue = _to_float(_find_col(row, ["营业收入", "营业总收入", "一、营业总收入"]))
    cogs = _to_float(_find_col(row, ["营业成本", "一、营业成本"]))
    if revenue and revenue > 0:
        return (revenue - cogs) / revenue * 100
    return 0.0


class AShareAdapter:
    """DataAdapter for Chinese A-Share market using AKShare (>= 1.12).

    New API layout: each row = one reporting period.
    Column '报告日' contains the period date (YYYYMMDD string).
    """

    def get_financial_statements(
        self, ticker: str, periods: int = 4
    ) -> list[FinancialStatements]:
        import akshare as ak

        sina_code = _ticker_to_sina(ticker)

        try:
            logger.info(f"Fetching financials for {sina_code}, periods={periods}")
            balance_df = ak.stock_financial_report_sina(stock=sina_code, symbol="资产负债表")
            income_df  = ak.stock_financial_report_sina(stock=sina_code, symbol="利润表")
            cf_df      = ak.stock_financial_report_sina(stock=sina_code, symbol="现金流量表")
        except Exception as e:
            raise DataCollectionError(f"AKShare fetch failed for {ticker}: {e}") from e

        if balance_df.empty:
            logger.warning(f"Empty balance sheet for {ticker}")
            return []

        # The first column is '报告日'; limit to requested number of periods
        results: list[FinancialStatements] = []
        for idx in range(min(periods, len(balance_df))):
            try:
                bs_row  = balance_df.iloc[idx]
                inc_row = income_df.iloc[idx]  if idx < len(income_df)  else pd.Series()
                cf_row  = cf_df.iloc[idx]      if idx < len(cf_df)      else pd.Series()

                period_str = str(bs_row.get("报告日", ""))
                if len(period_str) != 8:
                    continue
                period_date = date(int(period_str[:4]), int(period_str[4:6]), int(period_str[6:8]))

                revenue = _to_decimal(_find_col(inc_row, ["营业收入", "营业总收入", "一、营业总收入"]))
                net_profit = _to_decimal(_find_col(inc_row, [
                    "归属于母公司所有者的净利润", "净利润", "五、净利润"
                ]))
                total_assets = _to_decimal(_find_col(bs_row, ["资产总计", "资产合计"]))
                total_liab   = _to_decimal(_find_col(bs_row, ["负债合计", "负债总计"]))
                contract_liab = _to_decimal(_find_col(bs_row, ["合同负债"]), default=Decimal("0"))
                ocf = _to_decimal(_find_col(cf_row, [
                    "经营活动产生的现金流量净额", "经营活动现金流量净额"
                ]))
                eps  = _to_decimal(_find_col(inc_row, ["基本每股收益", "每股收益"]))
                bvps = _to_decimal(_find_col(bs_row,  ["每股净资产"]))

                equity = total_assets - total_liab
                gross_margin = _calculate_gross_margin(inc_row)
                roe = float(net_profit / equity * 100) if equity != 0 else 0.0

                results.append(FinancialStatements(
                    ticker=ticker,
                    period=period_date,
                    market=Market.A_SHARE,
                    revenue=revenue,
                    net_profit=net_profit,
                    gross_margin=gross_margin,
                    roe=roe,
                    contract_liabilities=contract_liab if contract_liab != 0 else None,
                    total_assets=total_assets,
                    total_liabilities=total_liab,
                    operating_cashflow=ocf,
                    eps=eps,
                    bvps=bvps,
                ))
            except Exception as e:
                logger.warning(f"Skip period idx={idx} for {ticker}: {e}")
                continue

        logger.info(f"Parsed {len(results)} periods for {ticker}")
        return results

    def get_price_history(
        self, ticker: str, start: date, end: date
    ) -> pd.DataFrame:
        import akshare as ak

        try:
            df = ak.stock_zh_a_hist(
                symbol=ticker,
                period="daily",
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                adjust="qfq",
            )
        except Exception as e:
            raise DataCollectionError(f"Price fetch failed for {ticker}: {e}") from e

        if df.empty:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

        column_map = {"日期": "date", "开盘": "open", "最高": "high",
                      "最低": "low", "收盘": "close", "成交量": "volume"}
        df = df.rename(columns=column_map)
        cols = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in df.columns]
        df = df[cols].copy()
        df["date"] = pd.to_datetime(df["date"]).dt.date
        return df.sort_values("date").reset_index(drop=True)

    def get_key_metrics(self, ticker: str) -> dict[str, float]:
        import akshare as ak

        try:
            df = ak.stock_a_lg_indicator(symbol=ticker)
        except Exception:
            try:
                df = ak.stock_individual_info_em(symbol=ticker)
            except Exception as e:
                raise DataCollectionError(f"Key metrics fetch failed for {ticker}: {e}") from e

        if df is None or df.empty:
            return {}

        result: dict[str, float] = {}
        # stock_a_lg_indicator returns rows with '指标' and '最新值'
        if "指标" in df.columns and "最新值" in df.columns:
            for _, row in df.iterrows():
                key = str(row["指标"])
                val = _to_float(row["最新值"])
                if "市盈率" in key:
                    result["pe"] = val
                elif "市净率" in key:
                    result["pb"] = val
                elif "市销率" in key:
                    result["ps"] = val
        return result

    def get_macro_indicators(self) -> dict[str, pd.Series]:
        import akshare as ak

        result: dict[str, pd.Series] = {}
        try:
            cpi = ak.macro_china_cpi_monthly()
            if not cpi.empty:
                result["CPI"] = pd.to_numeric(cpi.iloc[:, 1], errors="coerce").dropna()
        except Exception as e:
            logger.warning(f"CPI fetch failed: {e}")
        return result
