# valuation-agent

多行业估值监控与智能体辩证分析系统

基于 LangGraph 的多智能体架构，覆盖 A股 / 港股 / 美股跨市场估值分析。系统整合多源金融数据（AKShare / Tushare / yfinance），通过五层流水线（基础分析 → 投资大师辩论 → 多空辩论 → 风险证伪 → 综合估值）产出带风险调整的估值报告，并支持人工复核与决策反思闭环。

当前重点追踪标的：贵州茅台(600519)、五粮液(000858)、泸州老窖(000568)、片仔癀(600436)、达仁堂(600329)、泡泡玛特(09992)、Alphabet(GOOGL) 等，覆盖白酒、中药、潮玩、互联网等行业插件。

## 核心特性

- **L1-L5 分层分析流水线**：基本面/估值/情绪/行业分析 → 五位投资大师独立打分 → 多空研究员辩论 + 裁判仲裁 → 风险证伪官对抗性质疑 → 最终综合估值报告，支持人工复核（human-in-the-loop）中断/续跑
- **五位投资大师智能体**：Warren Buffett、Benjamin Graham、Charlie Munger、Philip Fisher、Aswath Damodaran，各自独立的投资哲学与打分逻辑
- **跨市场数据适配**：A股（AKShare/Tushare 双数据源）、港股（AKShare）、美股（yfinance），统一 `FinancialStatements` 数据模型
- **行业插件体系**：白酒、中药、潮玩、互联网等行业自定义指标（半自动采集 + 人工录入 + 告警规则），可扩展新行业
- **估值方法**：两阶段 DCF（含敏感性矩阵）、Monte Carlo 模拟（GBM 采样 growth/wacc/terminal growth）、Graham Number 安全边际、PE 历史分位带（3/5/10年）
- **新闻监控与事件分类**：RSS/新闻源采集 → 规则+LLM 分类（提价/政策/管理层/业绩/库存/竞对）→ 高优先级自动告警
- **RAG 检索**：BM25 风格的语义检索，用于给辩论/大师智能体提供文档证据（可扩展为 pgvector 混合检索）
- **反思记忆**：记录历史决策与实际结果对比，生成经验教训并反哺后续辩论上下文
- **多模型 LLM 路由**：按角色（debate_bull/debate_bear/risk_falsify/...）路由到不同模型，支持 fallback 链
- **Streamlit 可视化**：追踪公司总览、公司详情、行业对比、指标录入、报告导出
- **Grafana + TimescaleDB 监控栈**：时序指标存储与告警面板（docker-compose 一键启动）

## 系统架构

```
                          ┌─────────────────────────────┐
                          │         数据采集层             │
                          │ AKShare / Tushare / yfinance │
                          │  行业插件(半自动/人工/告警)      │
                          └───────────────┬───────────────┘
                                          │
                    ┌─────────────────────▼─────────────────────┐
                    │  L1  基础分析层 (Analysts)                    │
                    │  Fundamentals / Valuation / Sentiment /     │
                    │  Industry (竞对对比与行业格局)                  │
                    │  → DCF + Monte Carlo 计算                    │
                    └─────────────────────┬─────────────────────┘
                                          │
                    ┌─────────────────────▼─────────────────────┐
                    │  L2  投资大师层 (Masters)                     │
                    │  Buffett / Graham / Munger / Fisher /       │
                    │  Damodaran 独立打分 → Signal + Confidence    │
                    └─────────────────────┬─────────────────────┘
                                          │
                    ┌─────────────────────▼─────────────────────┐
                    │  L3  多空辩论层 (Debate Engine)               │
                    │  BullResearcher ⇄ BearResearcher            │
                    │  多轮辩论 → DebateJudge 仲裁 (stance+conf)    │
                    └─────────────────────┬─────────────────────┘
                                          │
                    ┌─────────────────────▼─────────────────────┐
                    │  L4  风险证伪层 (RiskFalsifier)               │
                    │  规则检查(PE分位/估值风险) + LLM 对抗性质疑     │
                    └─────────────────────┬─────────────────────┘
                                          │
                    ┌─────────────────────▼─────────────────────┐
                    │  L5  最终估值层 (FinalEstimator)              │
                    │  综合信号 → 估值区间(低/中/高) + 多空论据        │
                    │  → human_review (可选人工复核中断)             │
                    └─────────────────────┬─────────────────────┘
                                          │
                          ┌───────────────▼───────────────┐
                          │   ReflectionMemory (决策反思)    │
                          │   预测 vs 实际结果 → 经验教训       │
                          └───────────────────────────────┘
```

L1-L5 流水线由 `src/graph/pipeline.py` 中的 `ValuationPipeline` 编排，底层用 LangGraph 的 `StateGraph` 构建（`run()`），也提供不依赖 LangGraph 的顺序执行版本（`run_sequential()`，主要用于测试）。当 `RunConfig.require_human_approval=True` 时，L5 之后会插入 `human_review` 节点，通过 LangGraph 的 `interrupt`/`Command(resume=...)` 实现人工审批中断与续跑。

## 技术栈

| 层次 | 技术选型 |
|---|---|
| 智能体编排 | LangGraph, LangChain (core/openai/anthropic/community) |
| 数据源 | AKShare (A股/港股), Tushare (A股备用), yfinance (美股) |
| 数值计算 | NumPy, Pandas |
| 数据校验/配置 | Pydantic, pydantic-settings (YAML + .env 分层配置) |
| 存储 | PostgreSQL + TimescaleDB (时序指标) + pgvector (向量检索) |
| ORM | SQLAlchemy (async) |
| Web UI | Streamlit, Plotly |
| 监控可视化 | Grafana (Docker) |
| 任务调度 | APScheduler |
| 检索增强 | llama-index, sentence-transformers |
| 财务分析辅助 | financetoolkit, fredapi |
| 测试/Lint | pytest, ruff |

## 项目结构

```
valuation-agent/
├── src/
│   ├── agents/
│   │   ├── analysts/       # L1: fundamentals / valuation_analyst / sentiment / industry_analyst
│   │   ├── masters/        # L2: buffett / graham / munger / fisher / damodaran (base.py 定义抽象接口)
│   │   ├── debate/         # L3: bull / bear / judge / engine
│   │   ├── risk/           # L4: falsifier (风险证伪)
│   │   ├── final/          # L5: estimator (综合估值报告)
│   │   └── llm/            # LLM 路由、多模型配置、fallback 链、用量统计
│   ├── data/
│   │   ├── adapters/       # ashare (AKShare) / ashare_tushare / hk / us (yfinance) / fred / tradingview
│   │   ├── industry/       # 行业插件: baijiu(白酒) / tcm(中药) / toy(潮玩) / internet(互联网)
│   │   ├── company_manager.py   # 追踪公司管理
│   │   ├── competitor.py        # 竞对分析
│   │   └── collector.py         # 数据采集调度
│   ├── graph/
│   │   ├── pipeline.py     # ValuationPipeline: L1-L5 编排 (LangGraph)
│   │   └── state.py        # ValuationState / RunConfig
│   ├── valuation/
│   │   ├── dcf.py          # 两阶段DCF + 敏感性矩阵
│   │   ├── monte_carlo.py  # Monte Carlo 估值模拟
│   │   ├── graham.py       # Graham Number / 安全边际 / NCAV
│   │   ├── pe_band.py      # PE历史分位带 (3/5/10年)
│   │   ├── relative.py     # 相对估值
│   │   └── dupont.py       # 杜邦分析
│   ├── monitor/
│   │   ├── news.py         # 新闻采集
│   │   └── classifier.py   # 事件分类 (规则+LLM) 与告警触发
│   ├── memory/
│   │   └── reflection.py   # 决策反思记忆 (JSONL 持久化)
│   ├── rag/
│   │   ├── ingest.py       # 文档索引
│   │   └── search.py       # 混合检索 (BM25-like + 阈值判定)
│   ├── ui/
│   │   ├── app.py          # Streamlit 入口
│   │   └── pages/          # home / company_detail / industry_compare / metric_input / export
│   ├── db/
│   │   ├── models.py       # SQLAlchemy ORM 模型
│   │   └── engine.py
│   ├── schemas.py          # 全局 Pydantic 数据模型 (Signal, MasterSignal, DebateResult, ValuationReport...)
│   └── config.py           # Settings (YAML + .env 分层配置)
├── configs/
│   ├── settings.yaml       # 应用设置模板
│   ├── llm.yaml            # 多模型路由配置 (按角色路由 + fallback 链)
│   └── grafana/            # Grafana 数据源/看板/告警规则
├── docker/
│   └── init.sql            # TimescaleDB + pgvector 建表脚本
├── docker-compose.yml       # postgres(timescaledb) + grafana
├── tests/                   # pytest 单测: adapters / masters / pipeline / rag / valuation
├── .env.example
└── pyproject.toml
```

## 数据模型概览

核心 Pydantic 模型定义于 `src/schemas.py`：

- `Signal`：BULLISH / BEARISH / NEUTRAL 三态信号
- `MasterSignal`：投资大师输出（signal, confidence, reasoning, scoring_details）
- `FinancialStatements`：统一财务报表模型（跨 A股/港股/美股）
- `DCFAssumptions` / `DCFResult`：DCF 假设与结果（含敏感性矩阵）
- `MonteCarloResult`：模拟次数、百分位分布、均值/标准差
- `PEBandResult`：PE 分位带结果
- `DebateRound` / `DebateResult`：单轮辩论记录与最终裁决
- `ValuationReport`：最终报告（估值区间、多空论据、关键假设、敏感性因子、竞对对比、人工审批状态）
- `AlertRule` / `MetricDefinition` / `CollectionMode`：行业插件的指标定义与采集模式（AUTO/SEMI_AUTO/MANUAL）

PostgreSQL 表结构（`docker/init.sql`）对应持久化：`companies`, `financial_statements`, `industry_metrics`（TimescaleDB hypertable）, `master_signals`, `debate_records`, `valuation_reports`, `reflections`（含 pgvector embedding 列）。

## 快速开始

### 环境要求

- Python 3.11+
- Docker / Docker Compose（用于 PostgreSQL+TimescaleDB 和 Grafana）
- （可选）AKShare / Tushare / LLM API Key 用于真实数据接入

### 安装

```bash
git clone https://github.com/arthurdu98/valuation-agent.git
cd valuation-agent

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

### 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，按需填入：

```
DB_URL=postgresql://valuation:valuation_dev@localhost:5432/valuation
CLAUDE_API_KEY=
DEEPSEEK_API_KEY=
QWEN_API_KEY=
OPENAI_API_KEY=
TUSHARE_TOKEN=
FRED_API_KEY=
AKSHARE_ENABLED=true
LLM_CONFIG_PATH=configs/llm.yaml
DATA_COLLECTION_INTERVAL_HOURS=6
DEBUG=false
```

LLM 多模型路由在 `configs/llm.yaml` 中配置（当前默认模型 `deepseek-flash`，按角色 `debate_bull/debate_bear/debate_judge/risk_falsify/final_valuation/news_classify/reflection` 路由，并设有 fallback 链，可自行增加更多模型/角色映射）。

### 启动数据库与监控栈

```bash
docker compose up -d
```

会启动：
- `valuation-postgres`：TimescaleDB + pgvector + pgcrypto，自动执行 `docker/init.sql` 建表
- `valuation-grafana`（http://localhost:3000，默认账号 admin/admin）：预配置 PostgreSQL 数据源、看板与告警规则

### 运行 Streamlit UI

```bash
streamlit run src/ui/app.py
```

页面包括：追踪公司概览（Home）、公司详情、行业对比、手动指标录入、报告导出。

### 编程方式调用估值流水线

```python
from datetime import date
from decimal import Decimal
from src.graph.pipeline import ValuationPipeline
from src.schemas import Market

state = {
    "company": {"name": "贵州茅台"},
    "ticker": "600519",
    "industry": "白酒",
    "competitors": ["000858"],
    "financial_data": [{
        "ticker": "600519",
        "period": date(2024, 12, 31),
        "market": Market.A_SHARE,
        "revenue": Decimal("120"),
        "net_profit": Decimal("30"),
        "gross_margin": 65,
        "roe": 25,
        "total_assets": Decimal("200"),
        "total_liabilities": Decimal("50"),
        "operating_cashflow": Decimal("35"),
        "eps": Decimal("10"),
        "bvps": Decimal("50"),
    }],
}

result = ValuationPipeline().run_sequential(state)
print(result["final_report"])
```

需要 LangGraph 完整编排（含人工复核中断）时，改用 `ValuationPipeline(llm_router=...).run(state, config)`；`RunConfig` 支持设置 `debate_rounds`、`require_human_approval`、`thread_id`。人工复核后可通过 `pipeline.resume(thread_id, feedback)` 续跑。

## 测试

```bash
pytest tests/ -v
```

测试覆盖：
- `test_adapters.py`：数据适配器（A股/港股/美股）解析逻辑
- `test_masters.py`：五位投资大师智能体的信号生成
- `test_pipeline.py`：L1-L5 端到端顺序执行
- `test_rag.py`：检索引擎相关性排序与阈值判定
- `test_valuation.py`：DCF / Monte Carlo / PE分位带等估值方法

Lint：

```bash
ruff check src/ tests/
```

## 行业插件扩展

新增行业只需实现 `src/data/industry/base.py` 定义的插件协议（`industry` 属性 + `metrics: list[MetricDefinition]` + 可选 `AlertRule`），参考已有的 `baijiu.py`（白酒：产品结构、渠道库存、提价节奏）、`tcm.py`（中药：独家品种收入占比、集采风险）、`toy.py`（潮玩：IP生命周期、会员复购率）、`internet.py`（互联网：MAU/DAU、ARPU、CAC）实现。每个指标可标记采集模式（`AUTO`/`SEMI_AUTO`/`MANUAL`），供数据采集调度器与 Streamlit 录入页面区分处理方式。

## 已知限制

- `src/monitor`、`src/rag` 中部分能力（新闻源、向量检索）当前以规则/内存实现为主，生产环境建议接入真实 RAG 检索（pgvector 混合检索）与新闻 API
- Monte Carlo 与 DCF 计算基于经营性现金流(OCF)简化估算 FCF，实盘使用前建议结合更完整的自由现金流模型
- LLM 相关智能体（辩论、风险证伪、综合判断）在未配置 API Key 时会自动降级为规则/模板输出，不会报错中断流水线

## License

MIT License，详见 [LICENSE](LICENSE)。
