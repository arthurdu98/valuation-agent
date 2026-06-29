import logging
from dataclasses import dataclass
from src.monitor.news import RawNews
from src.agents.llm.router import LLMRouter

logger = logging.getLogger(__name__)

@dataclass
class ClassifiedEvent:
    title: str
    category: str  # price_change, inventory, policy, management, competitor, earnings, other
    severity: str  # critical, high, medium, low
    summary: str
    related_tickers: list[str]
    source_url: str = ""
    requires_alert: bool = False

class NewsClassifier:
    """Classifies news events using LLM and triggers alerts."""

    # High-priority event categories that trigger immediate alerts
    HIGH_PRIORITY_CATEGORIES = ["price_change", "policy", "management", "earnings"]

    # Keywords for rule-based pre-classification
    CATEGORY_KEYWORDS = {
        "price_change": ["提价", "调价", "涨价", "降价", "price increase", "price cut"],
        "policy": ["消费税", "反垄断", "监管", "集采", "regulation", "antitrust"],
        "management": ["董事长", "总经理", "人事变动", "辞职", "CEO", "resign"],
        "earnings": ["业绩", "财报", "营收", "净利润", "earnings", "revenue"],
        "inventory": ["库存", "渠道", "压货", "inventory"],
        "competitor": ["竞争", "市场份额", "competitor", "market share"],
    }

    def __init__(self, llm_router: LLMRouter | None = None):
        self._llm = llm_router

    def classify(self, news: RawNews) -> ClassifiedEvent | None:
        """Classify a news item into structured event.

        Returns None if the news is not relevant/actionable.
        """
        # Rule-based pre-classification
        category = self._rule_based_classify(news.title + " " + news.content[:200])

        if not category:
            # Use LLM for ambiguous cases
            if self._llm:
                category = self._llm_classify(news)
            else:
                category = "other"

        if category == "other":
            return None  # Not actionable

        severity = "high" if category in self.HIGH_PRIORITY_CATEGORIES else "medium"
        requires_alert = severity in ("critical", "high")

        return ClassifiedEvent(
            title=news.title,
            category=category,
            severity=severity,
            summary=news.content[:300] if news.content else news.title,
            related_tickers=news.related_tickers,
            source_url=news.url,
            requires_alert=requires_alert,
        )

    def _rule_based_classify(self, text: str) -> str | None:
        """Fast keyword-based classification."""
        text_lower = text.lower()
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return category
        return None

    def _llm_classify(self, news: RawNews) -> str:
        """LLM-based classification for ambiguous news."""
        prompt = f"""Classify this news into one category: price_change, inventory, policy, management, competitor, earnings, other

Title: {news.title}
Content: {news.content[:500]}

Reply with just the category name."""
        try:
            response = self._llm.call("news_classify", prompt)
            category = response.strip().lower().replace(" ", "_")
            if category in self.CATEGORY_KEYWORDS:
                return category
            return "other"
        except Exception:
            return "other"
