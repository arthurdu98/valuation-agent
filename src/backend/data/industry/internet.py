"""Internet (互联网) industry plugin implementation."""

from src.backend.schemas import AlertRule, CollectionMode, MetricDefinition


class InternetPlugin:
    """Industry plugin for Internet (互联网) sector.

    Tracks user growth (MAU/DAU), monetization efficiency (ARPU, take rate),
    acquisition cost (CAC), and revenue growth across ad and cloud segments.
    """

    @property
    def industry(self) -> str:
        return "互联网"

    @property
    def metrics(self) -> list[MetricDefinition]:
        return [
            MetricDefinition(
                name="mau",
                display_name="月活跃用户(MAU)",
                collection_mode=CollectionMode.SEMI_AUTO,
                description="月活跃用户数，百万",
            ),
            MetricDefinition(
                name="dau",
                display_name="日活跃用户(DAU)",
                collection_mode=CollectionMode.SEMI_AUTO,
                description="日活跃用户数，百万",
            ),
            MetricDefinition(
                name="arpu",
                display_name="每用户平均收入(ARPU)",
                collection_mode=CollectionMode.AUTO,
                description="ARPU = 营收/MAU，元或美元",
            ),
            MetricDefinition(
                name="cac",
                display_name="获客成本(CAC)",
                collection_mode=CollectionMode.SEMI_AUTO,
                description="单个新用户获取成本",
            ),
            MetricDefinition(
                name="ad_revenue_growth",
                display_name="广告收入增速%",
                collection_mode=CollectionMode.AUTO,
                description="广告业务收入同比增长率",
            ),
            MetricDefinition(
                name="cloud_revenue_growth",
                display_name="云业务收入增速%",
                collection_mode=CollectionMode.AUTO,
                description="云计算业务收入同比",
            ),
            MetricDefinition(
                name="take_rate",
                display_name="货币化率(Take Rate)%",
                collection_mode=CollectionMode.AUTO,
                description="平台GMV转化为营收的比率",
            ),
        ]

    def collect(self, company_ticker: str) -> dict[str, float]:
        """Collect internet metrics.

        Auto metrics from financial data, semi-auto from manual entry.
        """
        return {
            "mau": 0.0,
            "dau": 0.0,
            "arpu": 0.0,
            "cac": 0.0,
            "ad_revenue_growth": 0.0,
            "cloud_revenue_growth": 0.0,
            "take_rate": 0.0,
        }

    def get_alert_rules(self) -> list[AlertRule]:
        return [
            AlertRule(
                name="增长天花板预警",
                condition="mau_mom_change <= 0 AND cac_change_qoq > 0",
                threshold=0,
                severity="critical",
                description="MAU环比持平或下降且CAC上升，增长见顶信号",
            ),
            AlertRule(
                name="ARPU下滑",
                condition="arpu_change_qoq < threshold",
                threshold=-5.0,
                severity="warning",
                description="ARPU季度环比下降超过5%，变现效率恶化",
            ),
            AlertRule(
                name="广告增速放缓",
                condition="ad_revenue_growth < threshold",
                threshold=5.0,
                severity="warning",
                description="广告收入增速降至5%以下，核心变现引擎失速",
            ),
            AlertRule(
                name="获客成本飙升",
                condition="cac_change_qoq > threshold",
                threshold=20.0,
                severity="warning",
                description="CAC季度环比上升超过20%，用户获取边际回报递减",
            ),
        ]

    def get_bear_attack_points(self) -> list[str]:
        return [
            "用户增长见顶，MAU环比持平或下降",
            "获客成本(CAC)持续攀升，边际回报递减",
            "反垄断监管风险——罚款、业务拆分、互联互通",
            "广告收入增长放缓，被TikTok/短视频侵蚀份额",
            "AI颠覆风险——搜索/广告模式可能被AI agent替代",
            "数据隐私政策收紧限制精准广告能力",
        ]
