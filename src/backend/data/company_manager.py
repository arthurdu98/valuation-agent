"""Company management module for tracking and organizing companies."""

import logging
from typing import Optional

from src.backend.schemas import Company, Market

logger = logging.getLogger(__name__)


class CompanyManager:
    """Manages tracked companies for valuation analysis."""

    INITIAL_COMPANIES: list[dict] = [
        {"ticker": "600519", "name": "贵州茅台", "market": "a_share", "industry": "白酒", "competitors": ["000858", "000568"]},
        {"ticker": "000858", "name": "五粮液", "market": "a_share", "industry": "白酒", "competitors": ["600519", "000568"]},
        {"ticker": "000568", "name": "泸州老窖", "market": "a_share", "industry": "白酒", "competitors": ["600519", "000858"]},
        {"ticker": "600436", "name": "片仔癀", "market": "a_share", "industry": "中药", "competitors": []},
        {"ticker": "9992", "name": "泡泡玛特", "market": "hk", "industry": "潮玩", "competitors": []},
        {"ticker": "GOOGL", "name": "Alphabet/谷歌", "market": "us", "industry": "互联网", "competitors": ["MSFT", "META"]},
    ]
    _companies: dict[str, Company] = {
        item["ticker"]: Company(**item) for item in INITIAL_COMPANIES
    }

    def __init__(self, db_session=None):
        self._session = db_session

    def add_company(self, ticker: str, name: str, market: str, industry: str, competitors: Optional[list[str]] = None) -> Company:
        """Add a new company to tracking list. Returns Company schema."""
        company = Company(
            ticker=ticker,
            name=name,
            market=Market(market),
            industry=industry,
            competitors=competitors or [],
        )
        logger.info("Added company %s (%s) to tracking list", ticker, name)
        self._companies[ticker] = company
        return company

    def remove_company(self, ticker: str) -> bool:
        """Deactivate a company (keep history, stop collection)."""
        company = self._companies.get(ticker)
        if not company:
            return False
        company.is_active = False
        logger.info("Deactivated company %s", ticker)
        return True

    def get_tracked_companies(self) -> list[Company]:
        """Return all active tracked companies."""
        return [company for company in self._companies.values() if company.is_active]

    def update_competitors(self, ticker: str, competitors: list[str]) -> None:
        """Update competitor list for a company."""
        if ticker not in self._companies:
            raise KeyError(f"Company not tracked: {ticker}")
        self._companies[ticker].competitors = competitors
        logger.info("Updated competitors for %s: %s", ticker, competitors)

    def create_group(self, group_name: str, tickers: list[str]) -> None:
        """Create a custom company group."""
        for ticker in tickers:
            company = self._companies.get(ticker)
            if company and group_name not in company.custom_groups:
                company.custom_groups.append(group_name)
        logger.info("Created group '%s' with tickers: %s", group_name, tickers)

    def get_companies_by_industry(self, industry: str) -> list[Company]:
        """Get all tracked companies in an industry."""
        return [c for c in self.get_tracked_companies() if c.industry == industry]

    def get_companies_by_market(self, market: str) -> list[Company]:
        """Get all tracked companies in a market."""
        return [c for c in self.get_tracked_companies() if c.market.value == market]
