# Requirements Document: 多行业估值监控与智能体辩证分析系统

## Introduction

本系统是一个跨行业、跨市场的"上市公司估值 + 行业格局分析 + 竞争对手对标 + 关键指标追踪 + 多投资大师智能体辩证验证 → 最终估值判断"投研工具。系统不限于单一行业，而是支持用户追踪任意行业（白酒、潮玩、互联网、中药等）的上市公司，并在分析某家公司时自动纳入其竞争对手和行业格局上下文。

系统融合 ai-hedge-fund 的"大师打分范式"（确定性打分 + LLM 叙述）与 TradingAgents 的"多空辩论 + 反思记忆"，用 LangGraph 编排多智能体流水线，最终输出带假设、带区间、带多空论据的估值判断。

**初始追踪公司**：贵州茅台（A股）、五粮液（A股）、泸州老窖（A股）、片仔癀（A股）、泡泡玛特（港股）、谷歌/Alphabet（美股）——横跨白酒、中药、潮玩、互联网四个行业，涉及 A 股、港股、美股三个市场。

目标用户为具备 Python 开发能力的个人/小团队投研人员，系统定位为自用投研工具（非面向公众的持牌投顾产品）。

## Alignment with Product Vision

本软件的核心价值主张：
1. **跨行业通用估值框架**——将"价格（贵不贵）、商业模式（好不好）、企业文化（正不正）"三维分析编码为行业无关的通用估值引擎，同时支持行业特有指标插件化扩展
2. **竞争对手与行业格局联动**——分析任何一家公司时自动拉取同行业竞争对手数据，进行横向对比和相对估值，帮助理解行业地位
3. **将定性分析可证据化**——通过 RAG 从年报/业绩会/公告中抽取证据，让"商业模式质量"和"企业文化"等定性维度有据可查
4. **对抗性结构 > 单体全能**——通过多空辩论和证伪 agent 实现"辩证验证、辨明真理"
5. **运维收敛**——统一 Postgres 栈（TimescaleDB + pgvector + 关系表）降低小团队运维负担

## Requirements

### Requirement 1: 多市场财务数据采集与存储

**User Story:** As a 投研人员, I want 系统自动从多个数据源采集 A 股/港股/美股上市公司的财务数据, so that 我追踪的跨市场公司（茅台、泡泡玛特、谷歌等）都能获得统一格式的基础数据

#### Acceptance Criteria

1. WHEN 系统启动定时任务 THEN 系统 SHALL 根据公司所属市场选择对应数据源（A 股：AKShare/Tushare；港股：AKShare 港股接口/富途 OpenAPI；美股：yfinance/Financial Modeling Prep）采集财报三表，并存入统一 schema 的 TimescaleDB 表
2. IF 主数据源不可用 THEN 系统 SHALL 自动回退至备用源获取数据，并记录回退日志
3. WHEN 数据采集完成 THEN 系统 SHALL 提取各行业关键指标（白酒：合同负债/批价；中药：独家品种收入占比；互联网：MAU/ARPU；潮玩：会员复购率）并单独存储
4. WHEN 数据入库 THEN 系统 SHALL 同步采集宏观指标：中国宏观（CPI/M2/PMI/社融）通过 AKShare；美国宏观（Fed Funds Rate/CPI/Treasury Yields/Gold Price/Money Supply）通过 FRED API
5. IF 数据源连续 3 次采集失败 THEN 系统 SHALL 触发断流告警通知用户
6. WHEN 新增追踪公司 THEN 系统 SHALL 自动识别其所属市场和行业，配置对应的数据采集策略
7. WHEN 系统采集实时行情数据 THEN 系统 SHALL 通过 TradingView 数据接口获取跨市场（A 股/港股/美股/商品）的实时价格、技术指标和市场情绪数据

### Requirement 2: 行业与竞争对手识别

**User Story:** As a 投研人员, I want 系统能自动识别目标公司的行业归属和主要竞争对手, so that 我在研究某家公司时能同步了解行业格局和竞争态势

#### Acceptance Criteria

1. WHEN 用户添加追踪公司 THEN 系统 SHALL 自动识别其所属行业（支持用户手动修正），并检索同行业上市公司列表
2. WHEN 用户配置公司 THEN 系统 SHALL 允许用户手动指定主要竞争对手（如茅台 vs 五粮液/老窖；泡泡玛特 vs 名创优品/迪士尼消费品；谷歌 vs 微软/Meta）
3. WHEN 系统分析目标公司 THEN 系统 SHALL 自动拉取竞争对手的同期财务数据，生成横向对比表（营收增速、毛利率、ROE、PE 等核心指标排名）
4. WHEN 行业格局分析被触发 THEN 系统 SHALL 计算目标公司在行业中的市场份额（营收口径）、估值溢价/折价（vs 行业均值）、增速排名
5. IF 竞争对手发生重大事件（如提价、并购、业绩暴雷） THEN 系统 SHALL 推送关联提醒至目标公司的分析上下文

### Requirement 3: 行业特有指标管理（插件化）

**User Story:** As a 投研人员, I want 系统支持为不同行业定义特有的追踪指标, so that 白酒行业的"批价/合同负债"和互联网行业的"MAU/ARPU"能在同一框架下管理

#### Acceptance Criteria

1. WHEN 用户为某行业配置特有指标 THEN 系统 SHALL 支持定义指标名称、数据类型、采集方式（自动/半自动/手动）、告警阈值
2. WHEN 行业指标为"自动采集" THEN 系统 SHALL 通过配置的数据源接口定时获取（如 A 股合同负债来自 AKShare 资产负债表接口）
3. WHEN 行业指标为"半自动" THEN 系统 SHALL 提供录入界面，支持 LLM 视觉抽取截图数据预填（如白酒批价截图、潮玩新品发售公告）
4. WHEN 行业指标为"手动" THEN 系统 SHALL 提供结构化表单录入并校验数据合理性
5. WHEN 新行业被添加 THEN 系统 SHALL 提供行业指标模板（预置白酒/中药/互联网/潮玩常用指标），用户可在此基础上增删改

### Requirement 4: PE 历史分位带与 DCF 估值计算

**User Story:** As a 投研人员, I want 系统自动计算目标公司的 PE 历史分位带和 DCF 估值区间, so that 我能快速判断当前估值的历史位置和内在价值

#### Acceptance Criteria

1. WHEN 财务数据更新 THEN 系统 SHALL 自动计算最近 3/5/10 年 PE 的 10%/25%/50%/75%/90% 分位数
2. WHEN 用户请求 DCF 估值 THEN 系统 SHALL 基于用户输入的假设（增速、WACC、永续增长率）计算内在价值，并输出敏感性矩阵
3. WHEN DCF 计算完成 THEN 系统 SHALL 执行蒙特卡洛模拟（GBM 抽样增速/折现率），输出估值概率分布
4. IF 当前 PE 跌破历史 10% 分位 THEN 系统 SHALL 触发"估值极低"预警
5. WHEN 估值计算完成 THEN 系统 SHALL 同步计算杜邦分析（ROE 分解）和格雷厄姆数
6. WHEN 目标公司有已配置的竞争对手 THEN 系统 SHALL 同步计算竞争对手的 PE 分位和相对估值倍数对比

### Requirement 5: 投资大师智能体打分

**User Story:** As a 投研人员, I want 系统以多个投资大师的视角对目标公司进行独立打分, so that 我能从不同投资哲学的角度评估同一家公司

#### Acceptance Criteria

1. WHEN 用户触发估值分析 THEN 系统 SHALL 并行启动至少 5 个投资大师 agent（巴菲特、芒格、格雷厄姆、达摩达兰、费雪）
2. WHEN 大师 agent 执行分析 THEN 系统 SHALL 先执行确定性 Python 打分函数（基于该大师投资哲学的硬编码财务阈值），再调用 LLM 以该大师口吻叙述判断
3. WHEN 大师 agent 完成分析 THEN 系统 SHALL 输出统一格式 `{signal: bullish/bearish/neutral, confidence: 0-100, reasoning: string}`
4. WHEN 巴菲特 agent 分析 THEN 系统 SHALL 评估护城河强度、定价权、ROE 稳定性、盈利一致性——打分函数根据行业特性调整权重（如白酒看批价-出厂价价差，互联网看网络效应和用户锁定）
5. WHEN 格雷厄姆 agent 分析 THEN 系统 SHALL 计算安全边际、格雷厄姆数、流动比率、负债率
6. WHEN 达摩达兰 agent 分析 THEN 系统 SHALL 结合 narrative（story）与 DCF numbers 进行 disciplined valuation
7. WHEN 费雪 agent 分析 THEN 系统 SHALL 通过 RAG 检索年报/业绩会纪要，评估管理层质量和企业文化
8. WHEN 大师打分函数运行 THEN 系统 SHALL 根据目标公司所属行业加载对应的行业特有指标作为打分输入

### Requirement 6: 多空辩论与辩证验证

**User Story:** As a 投研人员, I want 系统对投资观点进行多空辩论和对抗性验证, so that 我能辨明分歧并发现潜在风险（如白酒的"压货"、互联网的"增长见顶"、潮玩的"潮流退热"）

#### Acceptance Criteria

1. WHEN 大师 agent 打分完成 THEN 系统 SHALL 启动 L3 多空辩论：Bull 研究员引用看多证据，Bear 研究员引用看空证据，进行可配置轮数的多轮交锋
2. WHEN 辩论进行 THEN 系统 SHALL 根据行业特性配置看空 agent 的专职攻击方向（白酒：压货假象；潮玩：IP 生命周期/复购衰减；互联网：监管/反垄断/增长天花板；中药：提价天花板/集采风险）
3. WHEN 辩论中引用论据 THEN 系统 SHALL 要求 agent 引用竞争对手数据作为对比论据（如"茅台增速不及五粮液""谷歌广告份额被 TikTok 侵蚀"）
4. WHEN 辩论结束 THEN 系统 SHALL 由 Research Manager（裁判 agent）总结双方论据强弱并给出综合判断
5. WHEN L3 辩论完成 THEN 系统 SHALL 启动 L4 风控/证伪 agent，对结论做对抗性证伪（检验行业周期风险、政策风险、估值透支等）
6. WHEN 辩论过程完成 THEN 系统 SHALL 保留完整辩论记录（每轮论据、引用证据、裁判评语），供用户回溯

### Requirement 7: 最终估值判断与人工闸门

**User Story:** As a 投研人员, I want 系统综合三维分析输出带区间和多空论据的最终估值判断，并在关键结论处暂停等待我确认, so that 我始终掌握最终决策权

#### Acceptance Criteria

1. WHEN L4 证伪完成 THEN 系统 SHALL 由 L5 最终估值 agent 综合价格/商业模式/企业文化三维，输出估值报告
2. WHEN 估值报告生成 THEN 系统 SHALL 包含：估值区间（低/中/高情景）、置信度、多空核心论据（各 3-5 条）、关键假设声明、敏感性因素、与竞争对手的相对估值对比
3. WHEN 关键估值结论生成 THEN 系统 SHALL 通过 LangGraph interrupt() 暂停流水线，等待用户确认后才将结论入库或触发告警
4. IF 用户拒绝估值结论 THEN 系统 SHALL 允许用户附加反馈意见，系统据此重新运行部分分析
5. WHEN 估值结论被确认 THEN 系统 SHALL 将结论存入历史库，供反思记忆模块学习

### Requirement 8: 新闻与公告监控

**User Story:** As a 投研人员, I want 系统实时监控追踪公司及其行业的相关新闻和公告, so that 我能第一时间获知提价、政策变动、竞争格局变化等关键事件

#### Acceptance Criteria

1. WHEN 系统启动监控 THEN 系统 SHALL 根据公司所属市场选择对应新闻源（A 股：CNINFO/财联社/东财；港股：港交所/智通财经；美股：SEC EDGAR/Google Finance/Reuters），通过 RSSHub 或 API 采集
2. WHEN 新闻/公告入库 THEN 系统 SHALL 调用 LLM 抽取/分类关键事件（提价、库存异常、经销商情绪、政策变动、管理层变动、并购重组、竞争对手动态）
3. IF 抽取到高优事件（提价、重大政策调整、业绩暴雷、管理层变动） THEN 系统 SHALL 立即触发推送告警
4. WHEN 监控到竞争对手的重大事件 THEN 系统 SHALL 自动关联至目标公司的分析上下文，并标注潜在影响
5. WHEN 新闻监控 agent 检测到行业级事件（如消费税改革、反垄断处罚、行业政策） THEN 系统 SHALL 关联至该行业所有追踪公司

### Requirement 9: RAG 研报/公告证据检索

**User Story:** As a 投研人员, I want 系统能从年报、业绩说明会纪要、研报中检索相关证据, so that "商业模式"和"企业文化"的评估有据可查而非 LLM 凭空判断

#### Acceptance Criteria

1. WHEN 用户上传年报/业绩会纪要/研报 PDF THEN 系统 SHALL 使用 LlamaIndex 进行切块（保留表格结构）、通过 BGE-M3 或 Qwen3-Embedding 生成向量，存入 pgvector，并标注所属公司和行业
2. WHEN 大师 agent 或辩论 agent 需要证据 THEN 系统 SHALL 执行混合检索（dense + BM25）→ RRF 融合 → cross-encoder 重排，返回最相关段落及来源标注
3. WHEN 检索目标公司证据时 THEN 系统 SHALL 支持跨公司检索竞争对手相关段落（如检索"白酒定价权"时同时返回茅台和五粮液相关证据）
4. WHEN 检索结果返回 THEN 系统 SHALL 附带原始文档引用（文件名、公司、页码/段落号），确保可溯源
5. IF 检索结果与查询相关性得分低于阈值 THEN 系统 SHALL 标注"证据不足"而非强行给出答案

### Requirement 10: 时序监控与复合告警

**User Story:** As a 投研人员, I want 系统对关键指标进行时序监控并设置复合告警规则, so that 我能在异常模式出现时第一时间收到预警

#### Acceptance Criteria

1. WHEN 时序数据更新 THEN 系统 SHALL 在 Grafana 仪表盘实时展示各追踪公司的关键指标走势
2. WHEN 用户为某公司/行业配置复合告警规则 THEN 系统 SHALL 支持多条件组合（如白酒"营收↑ + 合同负债↓ + 批价↓"= 压货预警；互联网"MAU↓ + 获客成本↑"= 增长见顶预警）
3. WHEN 告警触发 THEN 系统 SHALL 通过配置的通知渠道（邮件/webhook/飞书）推送告警详情
4. WHEN 用户查看告警 THEN 系统 SHALL 展示触发条件、关联数据图表、竞争对手同期指标对比、历史同类告警
5. WHEN 竞争对手的同类指标出现异常 THEN 系统 SHALL 将其作为对比信号展示（判断是个股问题还是行业问题）

### Requirement 11: 研究仪表盘与可视化

**User Story:** As a 投研人员, I want 通过直观的仪表盘查看估值分析全貌和行业对比, so that 我能快速掌握目标公司在行业中的位置和关键变化

#### Acceptance Criteria

1. WHEN 用户打开仪表盘 THEN 系统 SHALL 展示：量价利趋势图、毛利率/ROE 走势、关键行业指标、现金流、PE 分位带
2. WHEN 用户选择某公司 THEN 系统 SHALL 展示该公司与竞争对手的关键指标横向对比（雷达图/排名表）
3. WHEN 大师 agent 完成分析 THEN 系统 SHALL 展示各大师 `{signal, confidence, reasoning}` 卡片
4. WHEN 辩论完成 THEN 系统 SHALL 展示多空论据摘要、裁判结论、最终估值区间
5. WHEN 用户切换行业视图 THEN 系统 SHALL 展示该行业所有追踪公司的估值对比矩阵（PE/PB/PS 横向对比、估值分位排名）
6. WHEN 用户查看行业格局 THEN 系统 SHALL 展示市场份额、增速排名、盈利能力排名等行业地图

### Requirement 12: 反思记忆与学习

**User Story:** As a 投研人员, I want 系统能从历史决策的对错中学习, so that 辩论和估值判断"越用越准"

#### Acceptance Criteria

1. WHEN 估值结论被确认并经过一定时间（如季度）后 THEN 系统 SHALL 对比当时预测与实际结果，生成反思记录
2. WHEN 下次辩论启动 THEN 系统 SHALL 检索相关历史反思记忆（同公司/同行业/相似情景），供 agent 参考避免重复错误
3. WHEN 反思记录生成 THEN 系统 SHALL 标注"哪些论据正确/失败"，关联原始辩论记录
4. WHEN 行业内某公司的分析经验可迁移 THEN 系统 SHALL 在分析同行业其他公司时主动推荐相关历史教训

### Requirement 13: 公司与行业管理

**User Story:** As a 投研人员, I want 方便地添加、管理追踪公司和行业分组, so that 我的投研覆盖范围能灵活扩展

#### Acceptance Criteria

1. WHEN 用户添加新公司 THEN 系统 SHALL 支持通过股票代码/名称搜索，自动填充公司基本信息（市场、行业、市值、主营业务）
2. WHEN 公司被添加 THEN 系统 SHALL 自动建议竞争对手（基于行业分类和市值相近原则），用户可确认或修改
3. WHEN 用户创建行业分组 THEN 系统 SHALL 允许自定义分组（如"消费品：茅台+泡泡玛特+片仔癀"或"高端消费：茅台+五粮液+老窖"），不限于标准行业分类
4. WHEN 用户查看追踪列表 THEN 系统 SHALL 按行业分组展示所有追踪公司的实时状态概览（最新PE、距上次估值天数、待处理告警数）
5. WHEN 用户删除追踪公司 THEN 系统 SHALL 保留历史分析数据但停止主动采集和监控

### Requirement 14: 多模型 LLM 接入与配置

**User Story:** As a 投研人员, I want 系统能便捷接入任意 LLM（DeepSeek、Qwen、Claude、GPT 及任何 OpenAI 兼容 API）并灵活配置各 agent 使用的模型, so that 我能根据成本和效果自由选择和切换模型

#### Acceptance Criteria

1. WHEN 用户配置 LLM THEN 系统 SHALL 通过 YAML 配置文件统一管理所有模型提供商（支持 OpenAI、Anthropic、DeepSeek、Qwen/DashScope、Ollama 本地模型及任何 OpenAI 兼容 API endpoint）
2. WHEN 用户添加新模型提供商 THEN 系统 SHALL 仅需在配置文件中填写 provider 类型、base_url、api_key、model_name 即可接入，无需修改代码
3. WHEN 用户为各 agent 分配模型 THEN 系统 SHALL 支持在配置中为每个角色（大师叙述/辩论/裁判/证伪/新闻分类/反思）独立指定使用的模型和参数（temperature、max_tokens 等）
4. WHEN 配置中设置默认模型 THEN 系统 SHALL 对未单独指定模型的 agent 统一使用默认模型
5. IF 当前模型 API 调用失败 THEN 系统 SHALL 按配置的 fallback 链自动切换至备用模型（如 Claude → DeepSeek → Qwen → 本地 Ollama）
6. WHEN 用户希望降本 THEN 系统 SHALL 支持为叙述/分类等轻量任务分配低成本模型（如 DeepSeek/Qwen），为辩论/裁判等关键推理任务分配高能力模型（如 Claude/GPT）
7. WHEN 系统运行 THEN 系统 SHALL 记录每次 LLM 调用的模型名称、token 消耗、延迟和成本估算，供用户查看成本概览

## Non-Functional Requirements

### Performance

- 财务数据采集定时任务应在 10 分钟内完成全部追踪公司（跨三个市场）数据更新
- 单公司完整估值流水线（L1-L5）应在 10 分钟内完成
- RAG 检索响应时间应 < 3 秒（从查询发起到返回 top-5 结果）
- Streamlit 仪表盘页面加载时间 < 5 秒
- 行业横向对比查询（10 家以内公司）应在 5 秒内返回

### Security

- 所有 API Key（Tushare token、Claude API key、FRED API key、yfinance 等）通过环境变量或密钥管理服务存储，不硬编码
- 数据库连接使用 SSL/TLS 加密
- 用户上传的研报/年报文件存储在受控目录，不暴露外部访问

### Reliability

- 数据源采集实现市场级回退链（A 股：AKShare → Tushare → BaoStock；美股：yfinance → FMP；港股：AKShare → 富途；实时行情：TradingView；美国宏观：FRED API）
- LangGraph 流水线利用 checkpointing 实现崩溃后从精确状态恢复
- 所有 LLM 调用设置超时和重试机制，出错时 agent 兜底为 neutral 信号
- 系统支持 7×24 无人值守运行（监控 + 定时采集）
- 单个数据源故障不影响其他市场公司的正常分析

### Usability

- Streamlit UI 提供中文界面，操作流程符合投研人员习惯
- 支持截图 OCR 预填半自动指标录入，减少手动输入量
- 告警支持自定义阈值和通知渠道配置
- 估值报告支持导出为 Markdown/PDF 格式
- 系统提供清晰的错误提示和数据断流告知
- 添加新公司/新行业的操作应在 3 步内完成

### Scalability

- 初始覆盖 6 家公司（A 股 4 家 + 港股 1 家 + 美股 1 家），架构支持扩展至 30+ 公司
- 行业指标体系插件化，新增行业无需修改核心代码
- 大师 agent 架构支持新增大师（如彼得·林奇、塔勒布）而无需重构
- 数据源适配器模式，新增市场（如日股、英股）仅需新增适配器

### Constraints & Dependencies

- **批价等另类数据无公开 API**：白酒批价、潮玩二手价等行业特有数据依赖半自动录入
- **免费 A 股数据源均为爬虫**：AKShare/Tushare/BaoStock 依赖目标站不改版，需做断流告警
- **美股/港股数据源**：yfinance 免费但有限流风险；FMP/富途有免费额度但需注册
- **TradingView 数据源**：tradingview-scraper 和 Tradingview-API 为非官方接口，可能因 TradingView 改版失效，需做容错
- **FRED API**：免费但需申请 API Key，有每日请求限额（约 120 次/分钟），覆盖美联储全部公开经济数据
- **LLM 成本**：多 agent 辩论消耗大量 token，需支持混用 Claude + DeepSeek/本地模型降本
- **合规边界**：系统仅供自用投研，不对外提供荐股/估值建议服务
- **时区处理**：A 股/港股/美股交易时间不同，数据采集和告警需正确处理时区
