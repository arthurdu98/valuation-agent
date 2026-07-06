import logging
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

import httpx
from src.backend.schemas import Market

logger = logging.getLogger(__name__)

@dataclass
class RawNews:
    title: str
    content: str
    source: str
    published_at: datetime | None = None
    url: str = ""
    market: Market | None = None
    related_tickers: list[str] = field(default_factory=list)

class NewsMonitor:
    """Multi-market news and announcement monitor."""

    # News sources by market
    SOURCES = {
        Market.A_SHARE: ["cninfo", "eastmoney", "cls"],  # CNINFO公告, 东财, 财联社
        Market.HK: ["hkex", "aastocks"],
        Market.US: ["sec_edgar", "reuters"],
    }

    def __init__(self, rss_urls: dict[Market, list[str]] | None = None):
        self._seen_urls: set[str] = set()
        self._rss_urls = rss_urls or {}
        self._scheduler = None
        logger.info("NewsMonitor initialized")

    def fetch_news(self, market: Market, tickers: list[str] = None) -> list[RawNews]:
        """Fetch latest news for a market.

        Args:
            market: Target market
            tickers: Optional filter to specific companies

        Returns:
            List of RawNews items (deduplicated against seen_urls)
        """
        logger.info(f"Fetching news for {market.value} (tickers={tickers})")

        items: list[RawNews] = []
        for url in self._rss_urls.get(market, []):
            try:
                items.extend(self._fetch_rss(url, market, tickers or []))
            except Exception as exc:
                logger.warning("RSS fetch failed for %s: %s", url, exc)
        return self._deduplicate(items)

    def fetch_announcements(self, ticker: str, market: Market) -> list[RawNews]:
        """Fetch company-specific announcements/filings."""
        logger.info(f"Fetching announcements for {ticker} ({market.value})")
        return [
            news
            for news in self.fetch_news(market, [ticker])
            if ticker in news.related_tickers or ticker in news.title or ticker in news.content
        ]

    def start_monitoring(self, companies: list[dict], interval_minutes: int = 30):
        """Start periodic news monitoring for tracked companies."""
        logger.info(f"Starting news monitor for {len(companies)} companies, interval={interval_minutes}min")
        from apscheduler.schedulers.background import BackgroundScheduler

        self._scheduler = BackgroundScheduler()
        self._scheduler.add_job(
            lambda: [
                self.fetch_news(Market(company["market"]), [company["ticker"]])
                for company in companies
            ],
            trigger="interval",
            minutes=interval_minutes,
            id="news_monitor",
            replace_existing=True,
        )
        self._scheduler.start()

    def stop_monitoring(self):
        """Stop the news monitor."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown()
        logger.info("News monitor stopped")

    def _fetch_rss(self, url: str, market: Market, tickers: list[str]) -> list[RawNews]:
        response = httpx.get(url, timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        items = []
        for item in root.findall(".//item"):
            title = item.findtext("title", default="")
            content = item.findtext("description", default="")
            link = item.findtext("link", default="")
            published_text = item.findtext("pubDate", default="")
            published_at = None
            if published_text:
                try:
                    published_at = parsedate_to_datetime(published_text)
                except (TypeError, ValueError):
                    published_at = None
            related = [
                ticker for ticker in tickers if ticker in title or ticker in content
            ]
            if tickers and not related:
                continue
            items.append(
                RawNews(
                    title=title,
                    content=content,
                    source=url,
                    published_at=published_at,
                    url=link,
                    market=market,
                    related_tickers=related,
                )
            )
        return items

    def _deduplicate(self, items: list[RawNews]) -> list[RawNews]:
        deduped = []
        for item in items:
            key = item.url or f"{item.source}:{item.title}"
            if key in self._seen_urls:
                continue
            self._seen_urls.add(key)
            deduped.append(item)
        return deduped
