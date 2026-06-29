"""Main data collection orchestrator.

Coordinates data fetching across multiple market adapters with fallback
chains, scheduled collection, and failure alerting.
"""

from __future__ import annotations

import logging
from typing import Any

from src.data.company_manager import CompanyManager
from src.data.base import DataAdapter
from src.schemas import FinancialStatements, Market

logger = logging.getLogger(__name__)


class _NoopScheduler:
    """Fallback scheduler used when APScheduler is not installed."""

    running = False

    def add_job(self, *args, **kwargs) -> None:
        logger.warning("APScheduler is not installed; scheduled job not registered")

    def start(self) -> None:
        self.running = True
        logger.warning("APScheduler is not installed; scheduler running in noop mode")

    def shutdown(self) -> None:
        self.running = False


class DataCollector:
    """Orchestrates data collection across markets with fallback and scheduling.

    Maintains a registry of adapters per market, provides fallback chains
    when primary adapters fail, tracks consecutive failures, and supports
    periodic scheduled collection via APScheduler.
    """

    def __init__(self, adapters: dict[Market, list[DataAdapter]] | None = None) -> None:
        """Initialize adapters by market, scheduler, and failure tracking."""
        self._adapters = adapters or self._default_adapters()
        self._scheduler = self._create_scheduler()
        self._consecutive_failures: dict[str, int] = {}
        self._max_failures = 3

    def _default_adapters(self) -> dict[Market, list[DataAdapter]]:
        from src.data.adapters.ashare import AShareAdapter
        from src.data.adapters.us import USAdapter

        adapters: dict[Market, list[DataAdapter]] = {
            Market.A_SHARE: [AShareAdapter()],
            Market.US: [USAdapter()],
        }
        try:
            from src.data.adapters.hk import HKAdapter

            adapters[Market.HK] = [HKAdapter()]
        except Exception as exc:
            logger.info("HK adapter disabled: %s", exc)
            adapters[Market.HK] = []
        try:
            from src.data.adapters.ashare_tushare import TushareAdapter

            adapters[Market.A_SHARE].append(TushareAdapter())
        except Exception as exc:
            logger.info("Tushare fallback disabled: %s", exc)
        return adapters

    def _create_scheduler(self):
        try:
            from apscheduler.schedulers.background import BackgroundScheduler

            return BackgroundScheduler()
        except ImportError:
            return _NoopScheduler()

    def register_adapter(self, market: Market, adapter: DataAdapter, primary: bool = False) -> None:
        """Register a data adapter for a market."""
        self._adapters.setdefault(market, [])
        if primary:
            self._adapters[market].insert(0, adapter)
        else:
            self._adapters[market].append(adapter)

    def get_adapter(self, market: Market) -> DataAdapter:
        """Return primary adapter for given market.

        Args:
            market: The target market enum value.

        Returns:
            The first (primary) adapter registered for the market.

        Raises:
            KeyError: If no adapters are registered for the market.
        """
        return self._adapters[market][0]

    def collect_company_data(
        self, ticker: str, market: Market
    ) -> list[FinancialStatements] | None:
        """Collect data for a single company with fallback chain.

        Iterates through all registered adapters for the given market.
        On success, resets the failure counter. On total failure, increments
        the counter and triggers an alert if the threshold is reached.

        Args:
            ticker: Stock ticker symbol.
            market: The market the stock belongs to.

        Returns:
            List of FinancialStatements on success, or None if all adapters fail.
        """
        adapters = self._adapters.get(market, [])
        for adapter in adapters:
            try:
                data = adapter.get_financial_statements(ticker)
                self._consecutive_failures[ticker] = 0
                return data
            except Exception as e:
                logger.warning(
                    f"Adapter {type(adapter).__name__} failed for {ticker}: {e}"
                )
                continue

        # All adapters failed
        self._consecutive_failures[ticker] = (
            self._consecutive_failures.get(ticker, 0) + 1
        )
        if self._consecutive_failures[ticker] >= self._max_failures:
            self._trigger_alert(ticker)
        return None

    def collect_all(
        self, companies: list[tuple[str, Market]]
    ) -> dict[str, Any]:
        """Collect data for all tracked companies.

        Args:
            companies: List of (ticker, market) tuples to collect data for.

        Returns:
            Dictionary mapping ticker to collected FinancialStatements or None.
        """
        results: dict[str, Any] = {}
        for ticker, market in companies:
            results[ticker] = self.collect_company_data(ticker, market)
        return results

    def start_scheduler(self, interval_hours: int = 6) -> None:
        """Start periodic data collection.

        Adds a job that runs collect_all at the configured interval.
        The company list and interval can be overridden via settings.

        Args:
            interval_hours: Hours between collection runs (default 6).
        """
        from src.config import settings

        interval = settings.data_collection_interval_hours or interval_hours

        self._scheduler.add_job(
            func=self._scheduled_collect,
            trigger="interval",
            hours=interval,
            id="data_collection_job",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info(
            f"Data collection scheduler started with {interval}h interval"
        )

    def stop_scheduler(self) -> None:
        """Shut down the scheduler gracefully."""
        if self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("Data collection scheduler stopped")

    def _trigger_alert(self, ticker: str) -> None:
        """Trigger alert when consecutive failures exceed threshold.

        Args:
            ticker: The ticker that has been failing.
        """
        logger.critical(
            f"ALERT: {ticker} data collection failed "
            f"{self._max_failures} consecutive times"
        )

    def _scheduled_collect(self) -> None:
        """Internal method invoked by the scheduler.

        Loads the tracked company list and runs collect_all.
        Override or extend this to load companies from a database.
        """
        logger.info("Scheduled data collection triggered")
        manager = CompanyManager()
        companies = [
            (company.ticker, company.market)
            for company in manager.get_tracked_companies()
        ]
        if companies:
            self.collect_all(companies)
        else:
            logger.warning(
                "No companies configured for scheduled collection"
            )
