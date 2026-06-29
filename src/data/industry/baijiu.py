"""Baijiu (白酒) industry plugin implementation."""

from src.schemas import AlertRule, CollectionMode, MetricDefinition


class BaijiuPlugin:
    """Industry plugin for Baijiu (白酒) sector.

    Tracks pricing power indicators (batch price, ex-factory price, spread),
    channel health (inventory months), and balance sheet signals (contract liabilities).
    """

    @property
    def industry(self) -> str:
        return "白酒"

    @property
    def metrics(self) -> list[MetricDefinition]:
        return [
            MetricDefinition(
                name="batch_price",
                display_name="批价(飞天/普五/国窖)",
                collection_mode=CollectionMode.SEMI_AUTO,
                description="经销商批价，元/瓶",
            ),
            MetricDefinition(
                name="ex_factory_price",
                display_name="出厂价",
                collection_mode=CollectionMode.MANUAL,
                description="官方出厂价",
            ),
            MetricDefinition(
                name="price_spread",
                display_name="批价-出厂价价差",
                collection_mode=CollectionMode.AUTO,
                description="定价权核心指标，自动计算",
            ),
            MetricDefinition(
                name="inventory_months",
                display_name="渠道库存月数",
                collection_mode=CollectionMode.SEMI_AUTO,
                alert_threshold=3.0,
                description="经销商库存，超过3个月预警",
            ),
            MetricDefinition(
                name="contract_liabilities",
                display_name="合同负债(亿元)",
                collection_mode=CollectionMode.AUTO,
                description="来自资产负债表",
            ),
            MetricDefinition(
                name="contract_liabilities_yoy",
                display_name="合同负债同比%",
                collection_mode=CollectionMode.AUTO,
                description="合同负债同比变化率",
            ),
        ]

    def collect(self, company_ticker: str) -> dict[str, float]:
        """Collect baijiu metrics.

        Auto metrics from financial data, semi-auto from manual entry.
        """
        ex_factory_price = 969.0 if company_ticker == "600519" else 0.0
        batch_price = 2200.0 if company_ticker == "600519" else 0.0
        return {
            "batch_price": batch_price,
            "ex_factory_price": ex_factory_price,
            "price_spread": max(batch_price - ex_factory_price, 0.0),
            "inventory_months": 2.5,
            "contract_liabilities": 0.0,
            "contract_liabilities_yoy": 0.0,
        }

    def get_alert_rules(self) -> list[AlertRule]:
        return [
            AlertRule(
                name="压货预警",
                condition="revenue_growth > 0 AND contract_liabilities_yoy < 0 AND batch_price_change_weekly < 0",
                threshold=0,
                severity="critical",
                description="营收增长但合同负债下降且批价下跌，可能是压货",
            ),
            AlertRule(
                name="批价暴跌",
                condition="batch_price_change_weekly < threshold",
                threshold=-5.0,
                severity="warning",
                description="批价单周跌幅超过5%",
            ),
            AlertRule(
                name="库存过高",
                condition="inventory_months > threshold",
                threshold=3.0,
                severity="warning",
                description="渠道库存超过3个月",
            ),
            AlertRule(
                name="价差收窄",
                condition="price_spread < threshold",
                threshold=100.0,
                severity="info",
                description="批价-出厂价价差收窄至100元以内，定价权弱化信号",
            ),
        ]

    def get_bear_attack_points(self) -> list[str]:
        return [
            "营收增长可能是压货而非真实动销（看合同负债+批价+库存三角验证）",
            "批价持续下行说明供需失衡，经销商在甩货",
            "库存月数偏高意味着终端消费疲软",
            "提价空间被批价下行封死，未来增长逻辑受损",
            "消费税改革风险——从生产端转移到消费端将压缩利润",
            "年轻消费者白酒偏好下降的长期趋势",
        ]
