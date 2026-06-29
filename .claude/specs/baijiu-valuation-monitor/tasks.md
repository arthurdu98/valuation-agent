# Implementation Plan: 多行业估值监控与智能体辩证分析系统

## Task Overview

按照"先基础设施、再数据层、再计算引擎、再智能体、再展示"的顺序实现。分为 6 个阶段：
1. 项目骨架与基础设施（数据库、配置、核心接口）
2. 数据采集层（多市场适配器 + 行业插件）
3. 估值计算引擎
4. 智能体层（大师打分 + 辩论 + 证伪 + 终判）
5. RAG + 新闻监控 + 反思记忆
6. 仪表盘与告警

## Steering Document Compliance

- 项目结构遵循 design.md 中定义的 `src/` 子目录划分
- 使用 Python 3.11+、uv、Pydantic、Ruff
- 数据库统一使用 PostgreSQL + TimescaleDB + pgvector
- LLM 调用统一通过 LangChain ChatModel 抽象

## Atomic Task Requirements
**Each task must meet these criteria for optimal agent execution:**
- **File Scope**: Touches 1-3 related files maximum
- **Time Boxing**: Completable in 15-30 minutes
- **Single Purpose**: One testable outcome per task
- **Specific Files**: Must specify exact files to create/modify
- **Agent-Friendly**: Clear input/output with minimal context switching

## Tasks

### 阶段 1：项目骨架与基础设施

- [x] 1. 初始化项目结构和 pyproject.toml
  - Files: `pyproject.toml`, `src/__init__.py`, `README.md`
  - 使用 uv 初始化项目，配置 Python 3.11+ 依赖（langchain, langgraph, akshare, pandas, pydantic, sqlalchemy, streamlit）
  - 创建 src/ 子目录骨架（data/, valuation/, agents/, rag/, monitor/, memory/, graph/, ui/）
  - 配置 Ruff linter 规则
  - Purpose: 建立可运行的项目骨架
  - _Requirements: 全局_

- [x] 2. 创建核心数据模型（Pydantic schemas）
  - Files: `src/schemas.py`
  - 定义 Company, FinancialStatements, MasterSignal, DebateResult, ValuationReport 等 Pydantic BaseModel
  - 包含 Market enum (A_SHARE/HK/US)、Signal enum (BULLISH/BEARISH/NEUTRAL)
  - Purpose: 建立系统级类型安全基础
  - _Requirements: 1.1, 4.3, 5.3, 7.2_

- [x] 3. 创建数据库 ORM 模型和迁移脚本
  - Files: `src/db/models.py`, `src/db/engine.py`
  - 使用 SQLAlchemy 2.0 定义 Company, FinancialStatements, IndustryMetric, MasterSignalRecord, DebateRecord, ValuationReport, Reflection 表
  - 配置 TimescaleDB hypertable（IndustryMetric 按 recorded_at 分区）
  - 配置 pgvector 扩展（Reflection.embedding 列）
  - Purpose: 建立统一存储层
  - _Requirements: 1.1, 2.3, 9.1, 12.1_

- [x] 4. 创建 Docker Compose 配置（PostgreSQL + Grafana）
  - Files: `docker-compose.yml`, `docker/init.sql`
  - PostgreSQL 16 + TimescaleDB + pgvector 扩展
  - Grafana 配置自动连接 PostgreSQL 数据源
  - init.sql 创建扩展和初始 schema
  - Purpose: 一键启动开发环境
  - _Requirements: 9.1, 10.1_

- [x] 5. 创建配置管理模块
  - Files: `src/config.py`, `configs/settings.yaml`, `.env.example`
  - 使用 pydantic-settings 管理配置（API keys, DB URL, LLM 选择）
  - 支持环境变量覆盖和 yaml 配置文件
  - Purpose: 集中管理敏感配置和运行参数
  - _Requirements: NFR-Security_

- [x] 6. 创建 DataAdapter 协议接口
  - Files: `src/data/base.py`
  - 定义 DataAdapter Protocol：get_financial_statements, get_price_history, get_key_metrics, get_macro_indicators
  - 定义 FinancialStatements 返回结构（统一各市场 schema）
  - 定义回退链装饰器 `@with_fallback`
  - Purpose: 建立数据层的统一契约
  - _Requirements: 1.1, 1.2_

### 阶段 2：数据采集层

- [ ] 7. 实现 A 股数据适配器（AKShare）
  - Files: `src/data/adapters/ashare.py`
  - 实现 AShareAdapter(DataAdapter)：从 AKShare 获取 A 股财报三表、合同负债、宏观指标
  - 将 AKShare 返回的 DataFrame 转换为统一 schema
  - 实现错误重试和日志记录
  - Purpose: A 股主数据源接入
  - _Leverage: AKShare `stock_zcfz_em`, `stock_financial_report_sina`_
  - _Requirements: 1.1, 1.2_

- [ ] 8. 实现 A 股备用适配器（Tushare）
  - Files: `src/data/adapters/ashare_tushare.py`
  - 实现 TushareAdapter(DataAdapter)：从 Tushare Pro 获取 A 股财报
  - 处理积分制限流（rate limit backoff）
  - 将 Tushare schema 转换为统一格式
  - Purpose: A 股备用数据源
  - _Requirements: 1.2_

- [x] 9. 实现美股数据适配器（yfinance）
  - Files: `src/data/adapters/us.py`
  - 实现 USAdapter(DataAdapter)：从 yfinance 获取美股财报三表、价格历史
  - 处理 yfinance 的 Ticker 对象到统一 schema 的转换
  - Purpose: 美股数据源接入（支持谷歌）
  - _Requirements: 1.1, 1.6_

- [ ] 10. 实现港股数据适配器
  - Files: `src/data/adapters/hk.py`
  - 实现 HKAdapter(DataAdapter)：从 AKShare 港股接口获取港股财报
  - 处理港股特有的报告格式（半年报/年报为主）
  - Purpose: 港股数据源接入（支持泡泡玛特）
  - _Requirements: 1.1, 1.6_

- [x] 11. 实现数据采集回退链和调度器
  - Files: `src/data/collector.py`
  - 实现 DataCollector 类：按市场选择适配器，三级回退（AKShare→Tushare→BaoStock / yfinance→FMP）
  - 实现定时采集调度（APScheduler）
  - 连续 3 次失败触发断流告警
  - Purpose: 可靠的自动数据采集
  - _Requirements: 1.2, 1.5_

- [x] 11a. 实现 TradingView 数据适配器
  - Files: `src/data/adapters/tradingview.py`
  - 实现 TradingViewAdapter：通过 tradingview-scraper 获取跨市场实时行情和技术指标
  - 支持 A 股/港股/美股/商品（黄金等）的统一 symbol 映射
  - 获取 RSI/MACD/均线等技术指标供技术分析师 agent 使用
  - Purpose: 跨市场实时行情和技术面数据
  - _Leverage: https://github.com/mnwato/tradingview-scraper, https://github.com/Mathieu2301/Tradingview-API_
  - _Requirements: 1.7_

- [x] 11b. 实现 FRED 宏观数据适配器
  - Files: `src/data/adapters/fred.py`
  - 实现 FREDAdapter：通过 fredapi 获取美联储经济数据（Fed Funds Rate, Treasury Yields, Gold Price, CPI, M2, Unemployment 等）
  - 预置常用 series_id 映射（如 FEDFUNDS, DGS10, GOLDAMGBD228NLBM, CPIAUCSL）
  - 定时拉取 + 入 TimescaleDB 时序表
  - Purpose: 权威美国宏观经济数据源
  - _Leverage: https://fred.stlouisfed.org/docs/api/fred/_
  - _Requirements: 1.4_

- [x] 12. 实现行业插件基类和白酒插件
  - Files: `src/data/industry/base.py`, `src/data/industry/baijiu.py`
  - 定义 IndustryPlugin Protocol（collect, get_alert_rules, get_bear_attack_points）
  - 实现 BaijiuPlugin：批价录入、合同负债追踪、库存月数计算、"压货"攻击点
  - Purpose: 建立行业插件体系 + 白酒行业首个插件
  - _Requirements: 3.1, 3.2, 3.5_

- [x] 13. 实现互联网行业插件
  - Files: `src/data/industry/internet.py`
  - 实现 InternetPlugin：MAU/ARPU/获客成本/广告收入增速指标
  - 配置 Bear 攻击点："增长见顶""监管/反垄断""用户迁移"
  - Purpose: 支持谷歌等互联网公司分析
  - _Requirements: 3.1, 3.5_

- [x] 14. 实现中药行业插件
  - Files: `src/data/industry/tcm.py`
  - TCMPlugin：独家品种收入占比、集采风险指标、提价空间
  - 配置 Bear 攻击点："集采风险""提价天花板""老龄化依赖"
  - Purpose: 支持片仔癀分析
  - _Requirements: 3.1, 3.5_

- [x] 15. 实现潮玩行业插件
  - Files: `src/data/industry/toy.py`
  - ToyPlugin：IP 生命周期、复购率、盲盒溢价率、会员增长
  - 配置 Bear 攻击点："IP 生命周期衰减""潮流退热""复购率下滑"
  - Purpose: 支持泡泡玛特分析
  - _Requirements: 3.1, 3.5_

- [x] 16. 实现竞争对手分析器
  - Files: `src/data/competitor.py`
  - 实现 CompetitorAnalyzer：get_competitors, compare_metrics, industry_landscape, relative_position
  - 基于同行业 + 相近市值逻辑自动推荐竞对
  - 生成横向对比矩阵（营收增速/毛利率/ROE/PE 排名）
  - Purpose: 竞对对标和行业格局分析
  - _Requirements: 2.1, 2.3, 2.4_

- [x] 17. 实现公司管理模块
  - Files: `src/data/company_manager.py`
  - 实现公司添加（根据代码自动识别市场/行业）、竞对配置、自定义分组、追踪状态管理
  - 预置初始 6 家公司配置
  - Purpose: 公司和行业分组的 CRUD 操作
  - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

### 阶段 3：估值计算引擎

- [x] 18. 实现 PE 历史分位带计算
  - Files: `src/valuation/pe_band.py`
  - 基于 pandas rolling-quantile 计算 3/5/10 年 PE 的 10%/25%/50%/75%/90% 分位
  - 输出 PEBandResult（含当前位置、历史分布）
  - Purpose: 核心估值指标——PE 分位判断
  - _Requirements: 4.1, 4.4_

- [x] 19. 实现 DCF 估值和敏感性矩阵
  - Files: `src/valuation/dcf.py`
  - 实现自由现金流折现模型（两阶段 DCF）
  - 输出敏感性矩阵（增速 × WACC 网格）
  - 用户可配置假设参数（增速、WACC、永续增长率、预测年数）
  - Purpose: 内在价值估算
  - _Leverage: financetoolkit Models 模块参考_
  - _Requirements: 4.2_

- [x] 20. 实现蒙特卡洛模拟估值
  - Files: `src/valuation/monte_carlo.py`
  - 对增速和折现率做 GBM 随机抽样（N=10000 次）
  - 输出估值概率分布（P10/P25/P50/P75/P90）
  - Purpose: 估值区间的概率化表达
  - _Requirements: 4.3_

- [x] 21. 实现杜邦分析和格雷厄姆数
  - Files: `src/valuation/dupont.py`, `src/valuation/graham.py`
  - 杜邦：ROE = 净利率 × 总资产周转率 × 权益乘数，输出分解结果
  - 格雷厄姆数：sqrt(22.5 × EPS × BVPS)，计算安全边际百分比
  - Purpose: 辅助估值指标
  - _Leverage: financetoolkit Ratios 模块参考_
  - _Requirements: 4.5_

- [x] 22. 实现相对估值对比模块
  - Files: `src/valuation/relative.py`
  - 计算目标公司 vs 竞对的 PE/PB/PS/EV-EBITDA 对比
  - 输出估值溢价/折价百分比、行业排名
  - Purpose: 竞对视角的估值判断
  - _Requirements: 4.6, 2.4_

### 阶段 4：智能体层

- [x] 23. 创建 LLM 多模型配置文件
  - Files: `configs/llm.yaml`, `src/agents/llm/config.py`
  - 定义 YAML 配置结构：models（模型注册表）、role_routing（角色→模型映射）、fallback_chain（降级顺序）、default_model
  - 实现 LLMConfig / ModelConfig Pydantic 模型解析配置
  - 预置示例配置：Claude/DeepSeek/Qwen/GPT/Ollama 各一个模型定义
  - Purpose: 便捷的多模型声明式配置
  - _Requirements: 14.1, 14.2_

- [x] 23a. 实现 LLM Router 核心（多模型路由与调用）
  - Files: `src/agents/llm/router.py`
  - 实现 LLMRouter 类：get_model(role) 根据 role_routing 返回对应 LangChain ChatModel 实例
  - 支持 provider 类型：openai / anthropic / deepseek / qwen / ollama / openai_compatible
  - 实现 call(role, prompt, pydantic_model) 统一调用入口，带重试（指数退避）、超时、结构化输出
  - Purpose: 统一 LLM 调用层，屏蔽提供商差异
  - _Leverage: LangChain ChatModel 抽象 (ChatOpenAI, ChatAnthropic, ChatOllama)_
  - _Requirements: 14.3, 14.4_

- [x] 23b. 实现 LLM Fallback 降级与成本追踪
  - Files: `src/agents/llm/fallback.py`, `src/agents/llm/usage.py`
  - 实现 fallback 逻辑：当前模型失败时按 fallback_chain 顺序尝试下一个
  - 实现 UsageTracker：记录每次调用的模型名称、input/output tokens、延迟、估算成本
  - 提供 get_usage_stats() 返回累计统计
  - Purpose: 保证 LLM 调用可靠性 + 成本可见
  - _Requirements: 14.5, 14.7_

- [x] 24. 创建 MasterAgent 基类
  - Files: `src/agents/masters/base.py`
  - 定义 MasterAgent 抽象类：score() → 确定性打分，narrate() → LLM 叙述
  - 定义统一输出 MasterSignal(signal, confidence, reasoning)
  - 实现行业指标注入逻辑（根据公司行业加载对应 IndustryPlugin 数据）
  - Purpose: 大师 agent 的骨架
  - _Leverage: ai-hedge-fund 两段式范式_
  - _Requirements: 5.2, 5.3, 5.8_

- [x] 25. 实现巴菲特 Agent 打分函数
  - Files: `src/agents/masters/buffett.py`
  - 打分子函数：护城河评分、定价权评分（行业差异化：白酒看批价-出厂价差，互联网看网络效应）、ROE 稳定性、盈利一致性
  - 硬编码阈值（如 ROE > 20% → +3 分，连续 5 年增长 → +2 分）
  - LLM 叙述 prompt："You are Warren Buffett..."
  - Purpose: 第一个大师 agent 实现
  - _Leverage: ai-hedge-fund/src/agents/warren_buffett.py_
  - _Requirements: 5.4_

- [x] 26. 实现格雷厄姆 Agent 打分函数
  - Files: `src/agents/masters/graham.py`
  - 打分子函数：安全边际（当前价 vs 格雷厄姆数）、流动比率≥2、负债率<0.5、盈利稳定性
  - 计算 NCAV = 流动资产 - 总负债
  - Purpose: 价值投资/安全边际视角
  - _Leverage: ai-hedge-fund/src/agents/ben_graham.py_
  - _Requirements: 5.5_

- [x] 27. 实现达摩达兰 Agent 打分函数
  - Files: `src/agents/masters/damodaran.py`
  - 打分子函数：narrative 质量评分（增长 story 是否匹配 numbers）、DCF 输入合理性检查、disciplined valuation（不追热点）
  - 结合估值引擎 DCF 结果做 story-number 一致性检验
  - Purpose: Story + Numbers 纪律性估值视角
  - _Requirements: 5.6_

- [x] 28. 实现芒格 Agent 打分函数
  - Files: `src/agents/masters/munger.py`
  - 商业模式质量（毛利率稳定性、竞争壁垒、长坡厚雪）、管理层理性
  - 硬编码阈值（如毛利率 > 60% 且波动 < 5% → +3 分）
  - LLM 叙述 prompt："You are Charlie Munger..."
  - Purpose: 商业模式维度的评估
  - _Requirements: 5.7_

- [x] 29. 实现费雪 Agent 打分函数
  - Files: `src/agents/masters/fisher.py`
  - scuttlebutt 评分（通过 RAG 检索管理层言行、渠道关系证据），企业文化质量
  - 基于 RAG 检索结果进行证据化打分
  - LLM 叙述 prompt："You are Philip Fisher..."
  - Purpose: 企业文化维度的评估
  - _Requirements: 5.7_

- [x] 30. 实现基本面分析师和估值分析师
  - Files: `src/agents/analysts/fundamentals.py`, `src/agents/analysts/valuation_analyst.py`
  - 基本面分析师：量×价×结构分解，输出结构化基本面报告
  - 估值分析师：调用估值引擎汇总 PE/DCF/DDM 结论
  - Purpose: 为大师 agent 准备量化输入
  - _Requirements: 6.1_

- [x] 31. 实现舆情分析师和行业分析师
  - Files: `src/agents/analysts/sentiment.py`, `src/agents/analysts/industry_analyst.py`
  - 舆情分析师：汇总近期新闻事件，输出情绪评分
  - 行业分析师：调用 CompetitorAnalyzer 输出行业格局和竞对对比
  - Purpose: 为辩论提供舆情和行业上下文
  - _Requirements: 6.1, 6.3_

- [x] 32. 实现辩论引擎核心框架
  - Files: `src/agents/debate/engine.py`
  - 定义 DebateEngine 类：管理辩论轮次、状态流转、证据传递
  - 可配置辩论轮数（默认 3 轮）
  - 定义 DebateRound / DebateResult 数据结构
  - Purpose: 辩论模块的骨架和状态管理
  - _Leverage: muthuspark/multi-agent-debate 模板_
  - _Requirements: 6.1_

- [x] 33. 实现 Bull/Bear 研究员 Agent
  - Files: `src/agents/debate/bull.py`, `src/agents/debate/bear.py`
  - Bull 研究员：从大师看多信号和正面证据构建论点
  - Bear 研究员：从行业 bear_attack_points + 竞对数据构建反驳，专攻行业特有陷阱
  - 每轮可引用对方上一轮论据进行反驳
  - Purpose: 辩论的正反方实现
  - _Requirements: 6.2, 6.3_

- [x] 34. 实现辩论裁判 Agent
  - Files: `src/agents/debate/judge.py`
  - Research Manager（裁判）：总结双方论据强弱、评判证据质量、给出综合立场和置信度
  - 输出结构化 DebateResult
  - Purpose: 辩论仲裁和结论生成
  - _Requirements: 6.4_

- [x] 35. 实现 L4 风控/证伪 Agent
  - Files: `src/agents/risk/falsifier.py`
  - 对辩论结论做对抗性检验：政策风险、估值透支、行业周期、竞对威胁
  - 专门检验"看多结论是否忽略了关键风险"
  - 输出 RiskAssessment（风险等级、关键风险点列表）
  - Purpose: 最后一道安全网
  - _Requirements: 6.5_

- [x] 36. 实现 L5 最终估值 Agent
  - Files: `src/agents/final/estimator.py`
  - 综合三维（价格/商业模式/企业文化）+ 辩论结论 + 风控意见
  - 输出 ValuationReport：估值区间、置信度、多空论据、关键假设、竞对对比
  - Purpose: 生成最终估值判断
  - _Requirements: 7.1, 7.2_

- [x] 37. 实现 LangGraph 流水线状态定义
  - Files: `src/graph/state.py`
  - 定义 ValuationState TypedDict（company, industry, competitors, financial_data, industry_metrics, competitor_comparison, analyst_reports, master_signals, debate_result, risk_assessment, final_report, human_approved）
  - 定义 RunConfig 配置类（辩论轮数、模型选择、超时设置）
  - Purpose: 流水线状态模型
  - _Requirements: 7.3_

- [x] 38. 实现 LangGraph 流水线编排
  - Files: `src/graph/pipeline.py`
  - 构建 StateGraph：L1 并行 → L2 并行 → L3 辩论循环 → L4 证伪 → L5 终判 → interrupt()
  - 配置 PostgreSQL checkpointer（崩溃恢复）
  - 实现 `run(company, config)` 和 `resume(thread_id, feedback)`
  - Purpose: 将所有 agent 编排为可执行流水线
  - _Leverage: ai-hedge-fund 图拓扑 + LangGraph interrupt() 机制_
  - _Requirements: 7.3, 7.4, NFR-Reliability_

### 阶段 5：RAG + 新闻监控 + 反思记忆

- [ ] 39. 实现 RAG 文档摄取管线
  - Files: `src/rag/ingest.py`
  - PDF 解析 + 智能切块（保留表格结构，使用 LlamaIndex MarkdownNodeParser 或类似）
  - BGE-M3 嵌入生成 + pgvector 入库
  - 标注元数据（公司、文档类型、日期）
  - Purpose: 将研报/年报转为可检索的证据库
  - _Leverage: LlamaIndex PDF 摄取管线_
  - _Requirements: 9.1_

- [x] 40. 实现 RAG 混合检索引擎
  - Files: `src/rag/search.py`
  - Dense 检索（pgvector cosine similarity）+ BM25 稀疏检索
  - RRF 融合两路结果 → bge-reranker-v2-m3 重排
  - 支持跨公司检索（include_competitors=True）
  - 低相关性标注"证据不足"
  - Purpose: 高质量证据检索
  - _Requirements: 9.2, 9.3, 9.4, 9.5_

- [ ] 41. 实现新闻源采集模块
  - Files: `src/monitor/news.py`
  - 多市场新闻源接入（A 股：AKShare 公告 + RSSHub 财联社；美股：RSS；港股：RSS）
  - 定时拉取 + 去重 + 入库
  - 竞对事件自动关联至目标公司
  - Purpose: 新闻原始数据采集
  - _Requirements: 8.1, 8.4_

- [x] 42. 实现新闻事件分类器
  - Files: `src/monitor/classifier.py`
  - LLM 事件分类（提价/库存/政策/管理层/竞对动态）
  - 高优事件即时告警触发
  - 行业级事件关联至该行业所有追踪公司
  - Purpose: 新闻智能分类和告警触发
  - _Requirements: 8.2, 8.3, 8.5_

- [x] 43. 实现反思记忆模块
  - Files: `src/memory/reflection.py`
  - record_decision：存储已确认的估值决策
  - generate_reflection：对比预测 vs 实际，生成反思（调用 LLM）
  - retrieve_relevant：语义检索相关历史教训（pgvector）
  - 跨公司经验迁移（同行业检索）
  - Purpose: 系统越用越准的学习机制
  - _Requirements: 12.1, 12.2, 12.3, 12.4_

### 阶段 6：仪表盘与告警

- [x] 44. 实现 Streamlit 主页面（公司列表和行业分组）
  - Files: `src/ui/app.py`, `src/ui/pages/home.py`
  - 按行业分组展示所有追踪公司
  - 每家公司卡片：最新 PE、距上次估值天数、待处理告警数
  - 添加公司入口（搜索+自动填充）
  - Purpose: 系统入口和全局概览
  - _Requirements: 13.4, 11.1_

- [ ] 45. 实现公司详情页（估值+大师卡片+辩论摘要）
  - Files: `src/ui/pages/company_detail.py`
  - 财务指标趋势图（量价利/毛利率/ROE/现金流）
  - PE 分位带可视化
  - 大师 signal 卡片（5 张，含 confidence 条和 reasoning）
  - 辩论摘要（多空论据 + 裁判结论）
  - 最终估值区间展示
  - Purpose: 单公司深度分析视图
  - _Requirements: 11.1, 11.3, 11.4_

- [ ] 46. 实现行业对比页（竞对雷达图+排名表）
  - Files: `src/ui/pages/industry_compare.py`
  - 竞对横向对比表（营收增速/毛利率/ROE/PE 排名）
  - 雷达图对比核心指标
  - 估值对比矩阵（PE/PB/PS 横向）
  - 市场份额和增速排名行业地图
  - Purpose: 行业格局和相对估值视图
  - _Requirements: 11.2, 11.5, 11.6_

- [ ] 47. 实现 Grafana 告警规则配置
  - Files: `configs/grafana/dashboards/valuation.json`, `configs/grafana/alerts/rules.yaml`
  - 配置时序面板：批价走势、库存月数、合同负债变化、PE 分位
  - 配置复合告警规则（如"营收↑+合同负债↓+批价↓"压货预警）
  - 配置通知渠道（webhook/邮件）
  - Purpose: 7×24 自动监控告警
  - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [x] 48. 实现行业特有指标录入界面
  - Files: `src/ui/pages/metric_input.py`
  - 手动录入表单（批价、库存月数等）
  - 截图上传 + LLM 视觉抽取预填
  - 数据合理性校验
  - Purpose: 半自动另类数据录入
  - _Requirements: 3.3, 3.4_

- [x] 49. 实现估值报告导出
  - Files: `src/ui/export.py`
  - 将 ValuationReport 渲染为 Markdown（含图表占位）
  - 支持导出 PDF（通过 markdown → weasyprint）
  - 包含估值区间、多空论据、敏感性因素、竞对对比
  - Purpose: 研究成果的持久化输出
  - _Requirements: NFR-Usability_

- [x] 50. 编写估值引擎单元测试
  - Files: `tests/test_valuation.py`
  - 用已知财务数据验证 DCF/PE 分位/杜邦/格雷厄姆数计算正确性
  - 测试敏感性矩阵输出格式
  - Purpose: 确保估值计算核心正确性
  - _Requirements: NFR-Reliability_

- [x] 51. 编写数据适配器单元测试
  - Files: `tests/test_adapters.py`
  - Mock AKShare/yfinance API 响应验证 schema 转换正确性
  - 测试回退链故障切换逻辑
  - Purpose: 确保数据层可靠性
  - _Requirements: NFR-Reliability_

- [x] 52. 编写大师打分函数单元测试
  - Files: `tests/test_masters.py`
  - 预设财务数据验证各大师的阈值打分逻辑（不涉及 LLM）
  - 验证行业指标注入正确性
  - Purpose: 确保打分逻辑的确定性和可回测性
  - _Requirements: NFR-Reliability_

- [x] 53. 编写集成测试（流水线端到端）
  - Files: `tests/test_pipeline.py`
  - 单公司完整 L1-L5 流水线跑通（茅台，使用 Mock 数据）
  - 验证状态传递、checkpoint 保存/恢复、interrupt 暂停/resume
  - 回退链故障切换验证
  - Purpose: 验证组件协作正确性
  - _Requirements: NFR-Reliability, NFR-Performance_

- [x] 54. 编写 RAG 集成测试
  - Files: `tests/test_rag.py`
  - 测试 PDF 摄取 → 切块 → 嵌入 → 检索完整流程
  - 验证跨公司检索和相关性阈值逻辑
  - Purpose: 确保证据检索质量
  - _Requirements: 9.2, 9.5_
