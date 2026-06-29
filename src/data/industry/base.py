"""Base protocol for industry plugins."""

from typing import Protocol, runtime_checkable

from src.schemas import AlertRule, MetricDefinition


@runtime_checkable
class IndustryPlugin(Protocol):
    """Protocol defining the interface for industry-specific plugins.

    Each industry plugin provides:
    - Industry-specific metric definitions
    - Data collection logic for those metrics
    - Alert rules tailored to industry dynamics
    - Bear attack points for debate scenarios
    """

    @property
    def industry(self) -> str:
        """Industry name (e.g. '白酒', '互联网', '中药')."""
        ...

    @property
    def metrics(self) -> list[MetricDefinition]:
        """List of industry-specific metric definitions."""
        ...

    def collect(self, company_ticker: str) -> dict[str, float]:
        """Collect industry-specific metrics for a company.

        Returns:
            Dict mapping metric_name to its current value.
        """
        ...

    def get_alert_rules(self) -> list[AlertRule]:
        """Return alert rules specific to this industry."""
        ...

    def get_bear_attack_points(self) -> list[str]:
        """Return the key risk/attack points for bear researchers in debates."""
        ...
