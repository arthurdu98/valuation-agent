"""TCM (中药) industry plugin implementation."""

from src.schemas import AlertRule, CollectionMode, MetricDefinition


class TCMPlugin:
    """Industry plugin for TCM (中药) sector.

    Tracks exclusive variety revenue, pricing power, raw material costs,
    hospital sales channel mix, and centralized procurement (集采) risk
    for companies like 片仔癀.
    """

    @property
    def industry(self) -> str:
        return "中药"

    @property
    def metrics(self) -> list[MetricDefinition]:
        return [
            MetricDefinition(
                name="exclusive_variety_revenue_ratio",
                display_name="独家品种收入占比",
                collection_mode=CollectionMode.SEMI_AUTO,
                description="独家品种收入占总收入比例",
            ),
            MetricDefinition(
                name="core_product_price_increase_pct",
                display_name="核心产品提价幅度%",
                collection_mode=CollectionMode.MANUAL,
                description="核心产品年度提价幅度百分比",
            ),
            MetricDefinition(
                name="raw_material_price",
                display_name="原材料(天然麝香/牛黄)价格",
                collection_mode=CollectionMode.SEMI_AUTO,
                description="天然麝香、牛黄等关键原材料市场价格",
            ),
            MetricDefinition(
                name="hospital_sales_ratio",
                display_name="院内销售占比",
                collection_mode=CollectionMode.SEMI_AUTO,
                description="院内（医院）渠道销售收入占比",
            ),
            MetricDefinition(
                name="centralized_procurement_risk_index",
                display_name="集采风险指数",
                collection_mode=CollectionMode.MANUAL,
                alert_threshold=0.7,
                description="集采纳入风险综合评估指数，0-1范围",
            ),
        ]

    def collect(self, company_ticker: str) -> dict[str, float]:
        """Collect TCM metrics.

        Returns current known metrics with zeros for manually sourced data.
        """
        return {
            "exclusive_variety_revenue_ratio": 0.0,
            "core_product_price_increase_pct": 0.0,
            "raw_material_price": 0.0,
            "hospital_sales_ratio": 0.0,
            "centralized_procurement_risk_index": 0.0,
        }

    def get_alert_rules(self) -> list[AlertRule]:
        return [
            AlertRule(
                name="集采纳入预警",
                condition="centralized_procurement_risk_index > threshold",
                threshold=0.7,
                severity="critical",
                description="集采风险指数超过阈值，独家品种保护可能被突破",
            ),
            AlertRule(
                name="原材料涨价超阈值",
                condition="raw_material_price_change_pct > threshold",
                threshold=20.0,
                severity="warning",
                description="天然麝香/牛黄价格涨幅超过20%，成本压力加大",
            ),
            AlertRule(
                name="提价空间收窄",
                condition="core_product_price_increase_pct < threshold",
                threshold=3.0,
                severity="info",
                description="核心产品提价幅度低于3%，提价能力可能受限",
            ),
        ]

    def get_bear_attack_points(self) -> list[str]:
        return [
            "集采风险",
            "提价天花板——消费者承受力有限",
            "原材料稀缺推高成本",
            "独家品种保护到期风险",
            "医保控费压力",
            "消费降级影响高端中药消费",
        ]
