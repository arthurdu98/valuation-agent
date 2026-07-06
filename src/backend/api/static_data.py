"""Static comparison metrics for the pre-configured tracked companies.

Migrated from src/ui/pages/industry_compare.py (_STATIC_METRICS). In production
these come from AKShare/yfinance via DataCollector; kept static for the MVP so
the 行业对比 page renders without live data-source calls.
"""

from __future__ import annotations

STATIC_METRICS: dict[str, dict] = {
    "600519": {"name": "贵州茅台", "pe": 25.1, "pb": 8.6, "ps": 10.2,
               "gross_margin": 91.8, "roe": 34.2, "revenue_growth": 5.9,
               "net_margin": 46.9, "debt_ratio": 0.34, "market_cap_bn": 3200},
    "000858": {"name": "五粮液", "pe": 18.3, "pb": 5.1, "ps": 7.4,
               "gross_margin": 77.5, "roe": 33.5, "revenue_growth": 8.2,
               "net_margin": 35.1, "debt_ratio": 0.28, "market_cap_bn": 2100},
    "000568": {"name": "泸州老窖", "pe": 16.2, "pb": 4.8, "ps": 6.1,
               "gross_margin": 86.6, "roe": 22.7, "revenue_growth": -3.1,
               "net_margin": 38.4, "debt_ratio": 0.31, "market_cap_bn": 1450},
    "600436": {"name": "片仔癀", "pe": 42.5, "pb": 12.3, "ps": 15.1,
               "gross_margin": 68.2, "roe": 28.6, "revenue_growth": 12.4,
               "net_margin": 25.7, "debt_ratio": 0.22, "market_cap_bn": 580},
    "9992": {"name": "泡泡玛特", "pe": 14.9, "pb": 6.2, "ps": 5.3,
             "gross_margin": 72.1, "roe": 77.5, "revenue_growth": 185.0,
             "net_margin": 35.1, "debt_ratio": 0.29, "market_cap_bn": 2200},
    "GOOGL": {"name": "Alphabet", "pe": 21.4, "pb": 6.8, "ps": 6.3,
              "gross_margin": 57.9, "roe": 31.2, "revenue_growth": 14.3,
              "net_margin": 28.5, "debt_ratio": 0.14, "market_cap_bn": 22000},
}

# Mock financial history for a demo run (贵州茅台), mirrors company_detail.py.
MOCK_FINANCIALS: list[dict] = [
    {
        "period": "2024-12-31", "revenue": "159.4", "net_profit": "74.7",
        "gross_margin": 91.8, "roe": 34.2, "total_assets": "301.8",
        "total_liabilities": "102.3", "operating_cashflow": "66.2",
        "eps": "59.5", "bvps": "180.3",
    },
    {
        "period": "2023-12-31", "revenue": "150.6", "net_profit": "71.2",
        "gross_margin": 91.5, "roe": 35.1, "total_assets": "280.2",
        "total_liabilities": "95.8", "operating_cashflow": "62.1",
        "eps": "56.7", "bvps": "170.6",
    },
]

# Sample multi-year trend shown as a placeholder before any run completes.
SAMPLE_FINANCIAL_TREND: list[dict] = [
    {"year": 2020, "revenue": 94.9, "net_profit": 46.7, "gross_margin": 91.0, "roe": 31.9},
    {"year": 2021, "revenue": 106.2, "net_profit": 52.4, "gross_margin": 91.3, "roe": 31.7},
    {"year": 2022, "revenue": 127.8, "net_profit": 62.7, "gross_margin": 91.5, "roe": 33.3},
    {"year": 2023, "revenue": 150.6, "net_profit": 71.2, "gross_margin": 91.5, "roe": 35.1},
    {"year": 2024, "revenue": 159.4, "net_profit": 74.7, "gross_margin": 91.8, "roe": 34.2},
]
