# 本地运行指南（FastAPI + Next.js）

前端已从 Streamlit 迁移到 **FastAPI（后端 API）+ Next.js（前端）**，核心改进是 L1-L5 流水线的**实时进度流**（SSE）。

## 前置条件

- Docker Desktop（PostgreSQL + Grafana）
- Python 3.11 + `.venv`（已安装依赖）
- Node.js 20+（前端）

## 启动步骤

### 1. 基础设施（Docker）
```bash
docker compose up -d          # 仅 postgres + grafana
```
- PostgreSQL: `localhost:5432`
- Grafana: `http://localhost:3001`（本机 3000 被占用，已通过 docker-compose.override.yml 重映射）

### 2. 后端 API（FastAPI）
```bash
.venv/Scripts/python.exe -m uvicorn src.backend.api.main:app --port 8000
```
- API 文档: `http://localhost:8000/docs`
- 健康检查: `http://localhost:8000/api/health`

⚠ **必须单 worker 运行**：run_registry 和 CompanyManager 是进程内内存状态，多 worker 会静默分裂。

⚠ 启动命令须在**项目根目录**执行（`configs/llm.yaml` 等按相对根目录解析）。

### 3. 前端（Next.js）
```bash
cd src/frontend
npm run dev                   # http://localhost:3000
```
`/api/*` 通过 `next.config.ts` 的 rewrite 代理到 `localhost:8000`，本地开发免 CORS。

## 页面

| 路由 | 页面 | 说明 |
|---|---|---|
| `/` | 首页 | 按行业分组的追踪公司卡片 |
| `/companies/[ticker]` | 公司详情 | **运行估值分析 + 实时 L1-L5 进度**；4 Tab 结果 |
| `/compare` | 行业对比 | 对比表 + 估值/盈利分组柱图 + 雷达图 + 增速排名 |
| `/metrics` | 指标录入 | 按行业插件动态生成指标表单 |
| `/reports` | 报告导出 | 已完成 run 的 Markdown / PDF 下载 |

## 快速验证

```bash
# 用 Mock 数据跑一次分析（无需 API key，规则模式）
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"ticker":"600519","use_mock":true,"debate_rounds":1}'

# 用返回的 run_id 观察实时进度
curl -N http://localhost:8000/api/runs/<run_id>/stream
```

## 已知限制（MVP）

- **人工复核续跑**（HITL）：`/api/runs/{id}/resume` 返回 501。InMemorySaver 单进程约束，后续接 Postgres checkpointer 再启用。
- **DB 未接线**：公司列表、指标提交为内存/回显；`GET /api/metrics/{ticker}` 返回空数组。
- **无鉴权**：run 端点会触发付费 LLM 调用。非 localhost 暴露前必须加 API key + 限流。
- **行业对比数据**为静态样例（`src/backend/api/static_data.py`），生产环境应接 DataCollector。
