"""TradingView real-time data adapter.

Supplementary data source for real-time quotes and technical indicators
using the tradingview_scraper library. This is NOT a primary DataAdapter
(does not implement the DataAdapter protocol) — it provides complementary
real-time market data.

NOTE: tradingview_scraper is an unofficial, community-maintained library
that scrapes TradingView data. It may break without notice if TradingView
changes their website structure or API. Use with appropriate error handling
and do not rely on it for mission-critical data pipelines.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from src.schemas import RealtimeQuote

logger = logging.getLogger(__name__)

# Lazy import to avoid hard failure if library API changes
try:
    from tradingview_scraper.symbols.technicals import Indicators
    _TV_AVAILABLE = True
except ImportError:
    _TV_AVAILABLE = False
    logger.warning("tradingview_scraper not available or API changed. TradingViewAdapter will be non-functional.")


class TradingViewAdapter:
    """Supplementary real-time data source using TradingView.

    Provides real-time quotes and technical indicators via the
    tradingview_scraper library's Indicators class.

    NOTE: Relies on the unofficial tradingview_scraper library which
    may experience instability due to upstream website changes.
    """

    SYMBOL_MAP: dict[str, str] = {
        "600519": "SSE:600519",    # Moutai
        "000568": "SZSE:000568",   # Luzhou Laojiao
        "000858": "SZSE:000858",   # Wuliangye
        "600436": "SSE:600436",    # Pian Zi Huang
        "9992": "HKEX:9992",       # Pop Mart
        "GOOGL": "NASDAQ:GOOGL",   # Google
        "MSFT": "NASDAQ:MSFT",     # Microsoft
        "META": "NASDAQ:META",     # Meta
        "GOLD": "TVC:GOLD",
        "XAUUSD": "OANDA:XAUUSD",
        "GC": "COMEX:GC1!",
    }

    # Technical indicators to fetch
    DEFAULT_INDICATORS = [
        "RSI", "MACD.macd", "MACD.signal",
        "EMA20", "EMA50", "SMA20", "SMA50", "SMA200",
        "ADX", "ATR", "CCI20", "Stoch.K", "Stoch.D",
    ]

    def __init__(self) -> None:
        """Initialize TradingView adapter."""
        self._available = _TV_AVAILABLE
        if self._available:
            self._indicators = Indicators()
            logger.info("TradingViewAdapter initialized successfully")
        else:
            self._indicators = None
            logger.warning("TradingViewAdapter initialized in degraded mode (library unavailable)")

    def resolve_symbol(self, ticker: str) -> str:
        """Map a common ticker to TradingView symbol format.

        Args:
            ticker: Plain ticker string (e.g., "600519", "GOOGL").

        Returns:
            TradingView-formatted symbol (e.g., "SSE:600519", "NASDAQ:GOOGL").
            If no mapping exists, returns the ticker as-is.
        """
        resolved = self.SYMBOL_MAP.get(ticker, ticker)
        logger.debug(f"Resolved ticker '{ticker}' -> '{resolved}'")
        return resolved

    def _parse_exchange_symbol(self, tv_symbol: str) -> tuple[str, str]:
        """Parse 'EXCHANGE:SYMBOL' format into (exchange, symbol)."""
        if ":" in tv_symbol:
            exchange, symbol = tv_symbol.split(":", 1)
            return exchange, symbol
        return "", tv_symbol

    def get_realtime_quote(self, symbol: str) -> RealtimeQuote:
        """Fetch a real-time quote for a single symbol.

        Args:
            symbol: TradingView-formatted symbol (e.g., "SSE:600519")
                    or plain ticker (will be resolved via SYMBOL_MAP).

        Returns:
            RealtimeQuote with current price, change percent, and volume.

        Raises:
            RuntimeError: If the quote cannot be fetched.
        """
        if not self._available:
            raise RuntimeError("TradingView scraper library not available")

        tv_symbol = self.resolve_symbol(symbol)
        exchange, sym = self._parse_exchange_symbol(tv_symbol)

        try:
            logger.info(f"Fetching realtime quote for {tv_symbol}")
            data = self._indicators.scrape(
                exchange=exchange,
                symbol=sym,
                indicators=["close", "change", "volume"],
            )

            price = float(data.get("close", 0.0))
            change_pct = float(data.get("change", 0.0))
            volume_raw = data.get("volume")
            volume: Optional[int] = int(volume_raw) if volume_raw is not None else None

            return RealtimeQuote(
                symbol=tv_symbol,
                price=price,
                change_pct=change_pct,
                volume=volume,
                timestamp=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Failed to fetch quote for {tv_symbol}: {e}")
            raise RuntimeError(f"Failed to fetch quote for {tv_symbol}: {e}") from e

    def get_technical_indicators(self, symbol: str) -> dict[str, float]:
        """Fetch technical indicators for a symbol.

        Args:
            symbol: TradingView-formatted symbol or plain ticker.

        Returns:
            Dict mapping indicator names to values (e.g., {"RSI": 55.3, "MACD.macd": 1.2}).

        Raises:
            RuntimeError: If indicators cannot be fetched.
        """
        if not self._available:
            raise RuntimeError("TradingView scraper library not available")

        tv_symbol = self.resolve_symbol(symbol)
        exchange, sym = self._parse_exchange_symbol(tv_symbol)

        try:
            logger.info(f"Fetching technical indicators for {tv_symbol}")
            data = self._indicators.scrape(
                exchange=exchange,
                symbol=sym,
                indicators=self.DEFAULT_INDICATORS,
            )

            # Filter out None values and convert to float
            result = {}
            for key, value in data.items():
                if value is not None:
                    try:
                        result[key] = float(value)
                    except (ValueError, TypeError):
                        logger.debug(f"Skipping non-numeric indicator {key}={value}")
            return result

        except Exception as e:
            logger.error(f"Failed to fetch indicators for {tv_symbol}: {e}")
            raise RuntimeError(f"Failed to fetch indicators for {tv_symbol}: {e}") from e

    def get_market_summary(self, symbols: list[str]) -> list[RealtimeQuote]:
        """Batch fetch quotes for multiple symbols.

        Args:
            symbols: List of TradingView-formatted symbols or plain tickers.

        Returns:
            List of RealtimeQuote objects. Failed fetches are skipped with a warning.
        """
        quotes = []
        for symbol in symbols:
            try:
                quote = self.get_realtime_quote(symbol)
                quotes.append(quote)
            except Exception as e:
                logger.warning(f"Skipping {symbol} in market summary: {e}")
        return quotes
