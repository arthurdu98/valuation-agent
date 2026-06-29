"""Toy (潮玩) industry plugin implementation."""

from src.schemas import AlertRule, CollectionMode, MetricDefinition


class ToyPlugin:
    """Industry plugin for Toy (潮玩) sector.

    Tracks IP lifecycle health, member engagement, blind box premium,
    new IP contribution, membership scale, and overseas expansion
    for companies like 泡泡玛特.
    """

    @property
    def industry(self) -> str:
        return "潮玩"

    @property
    def metrics(self) -> list[MetricDefinition]:
        return [
            MetricDefinition(
                name="ip_lifecycle_index",
                display_name="IP生命周期指数",
                collection_mode=CollectionMode.SEMI_AUTO,
                description="IP热度与生命周期综合评估指数",
            ),
            MetricDefinition(
                name="member_repurchase_rate_pct",
                display_name="会员复购率%",
                collection_mode=CollectionMode.SEMI_AUTO,
                alert_threshold=50.0,
                description="会员复购率百分比，低于50%预警",
            ),
            MetricDefinition(
                name="blind_box_premium_rate_pct",
                display_name="盲盒溢价率%",
                collection_mode=CollectionMode.SEMI_AUTO,
                description="二手市场盲盒溢价率，反映热度",
            ),
            MetricDefinition(
                name="new_ip_contribution_pct",
                display_name="新IP贡献占比%",
                collection_mode=CollectionMode.SEMI_AUTO,
                description="新IP收入贡献占总收入百分比",
            ),
            MetricDefinition(
                name="member_count_wan",
                display_name="会员数(万)",
                collection_mode=CollectionMode.AUTO,
                description="累计注册会员数，单位万人",
            ),
            MetricDefinition(
                name="overseas_revenue_ratio_pct",
                display_name="海外收入占比%",
                collection_mode=CollectionMode.SEMI_AUTO,
                description="海外市场收入占总收入百分比",
            ),
        ]

    def collect(self, company_ticker: str) -> dict[str, float]:
        """Collect toy/pop mart metrics.

        Returns current known metrics with zeros for manually sourced data.
        """
        return {
            "ip_lifecycle_index": 0.0,
            "member_repurchase_rate_pct": 0.0,
            "blind_box_premium_rate_pct": 0.0,
            "new_ip_contribution_pct": 0.0,
            "member_count_wan": 0.0,
            "overseas_revenue_ratio_pct": 0.0,
        }

    def get_alert_rules(self) -> list[AlertRule]:
        return [
            AlertRule(
                name="复购率下滑预警",
                condition="member_repurchase_rate_pct < threshold",
                threshold=50.0,
                severity="warning",
                description="会员复购率低于50%，用户粘性下降",
            ),
            AlertRule(
                name="单一IP依赖过高",
                condition="top1_ip_revenue_ratio > threshold",
                threshold=0.4,
                severity="warning",
                description="单一IP收入占比超过40%，集中度风险",
            ),
            AlertRule(
                name="盲盒溢价率归零(热度消退)",
                condition="blind_box_premium_rate_pct < threshold",
                threshold=5.0,
                severity="critical",
                description="盲盒二手溢价率低于5%，表明热度消退",
            ),
        ]

    def get_bear_attack_points(self) -> list[str]:
        return [
            "IP生命周期衰减——Molly/DIMOO热度不可能永远持续",
            "潮流退热——盲盒/潮玩是周期性消费非刚需",
            "复购率下滑意味着用户流失",
            "竞争加剧——名创优品/52TOYS/泡泡玛特模仿者",
            "海外扩张不确定性——文化差异和渠道壁垒",
            "库存风险——非爆款IP积压",
        ]
