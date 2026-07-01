"""Company detail page — financial trends, master signals, debate, valuation."""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from decimal import Decimal
from datetime import date

from src.data.company_manager import CompanyManager


def _signal_color(signal: str) -> str:
    return {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}.get(signal.lower(), "⚪")


def _confidence_bar(conf: float) -> str:
    filled = int(conf / 10)
    return "█" * filled + "░" * (10 - filled) + f"  {conf:.0f}%"


def render_company_detail():
    st.header("公司详情分析")
    cm = CompanyManager()
    companies = cm.get_tracked_companies()
    if not companies:
        st.warning("暂无追踪公司，请先在首页添加。")
        return

    selected = st.selectbox("选择公司", [f"{c.name}  ({c.ticker})" for c in companies])
    ticker = selected.split("(")[1].rstrip(")")
    company = next((c for c in companies if c.ticker == ticker), None)
    if not company:
        return

    # ── 基本信息 ─────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("公司", company.name)
    col2.metric("行业", company.industry)
    col3.metric("市场", company.market.value.upper())
    col4.metric("竞争对手", len(company.competitors))

    st.divider()

    # ── 运行估值流水线 ────────────────────────────────────────
    with st.expander("▶ 运行估值分析（需要真实财务数据或 Mock 数据）", expanded=False):
        use_mock = st.checkbox("使用内置 Mock 数据（茅台示例）", value=True)
        debate_rounds = st.slider("辩论轮数", 1, 5, 2)

        if st.button("🚀 开始分析", type="primary"):
            with st.spinner("L1-L5 流水线运行中，约 2-4 分钟…"):
                try:
                    from src.agents.llm.router import LLMRouter
                    from src.graph.pipeline import ValuationPipeline
                    from src.graph.state import RunConfig
                    from src.schemas import Market

                    router = LLMRouter("configs/llm.yaml")
                    cfg = RunConfig(debate_rounds=debate_rounds, require_human_approval=False)
                    pipeline = ValuationPipeline(llm_router=router, run_config=cfg)

                    if use_mock:
                        state = {
                            "company": {"name": company.name},
                            "ticker": company.ticker,
                            "industry": company.industry,
                            "competitors": company.competitors,
                            "financial_data": [
                                {
                                    "ticker": company.ticker,
                                    "period": date(2024, 12, 31),
                                    "market": Market.A_SHARE,
                                    "revenue": Decimal("159.4"),
                                    "net_profit": Decimal("74.7"),
                                    "gross_margin": 91.8,
                                    "roe": 34.2,
                                    "total_assets": Decimal("301.8"),
                                    "total_liabilities": Decimal("102.3"),
                                    "operating_cashflow": Decimal("66.2"),
                                    "eps": Decimal("59.5"),
                                    "bvps": Decimal("180.3"),
                                },
                                {
                                    "ticker": company.ticker,
                                    "period": date(2023, 12, 31),
                                    "market": Market.A_SHARE,
                                    "revenue": Decimal("150.6"),
                                    "net_profit": Decimal("71.2"),
                                    "gross_margin": 91.5,
                                    "roe": 35.1,
                                    "total_assets": Decimal("280.2"),
                                    "total_liabilities": Decimal("95.8"),
                                    "operating_cashflow": Decimal("62.1"),
                                    "eps": Decimal("56.7"),
                                    "bvps": Decimal("170.6"),
                                },
                            ],
                            "industry_metrics": {"price_spread": 350, "batch_price": 2100},
                        }
                    else:
                        state = {
                            "company": {"name": company.name},
                            "ticker": company.ticker,
                            "industry": company.industry,
                            "competitors": company.competitors,
                            "financial_data": [],
                            "industry_metrics": {},
                        }

                    result = pipeline.run_sequential(state)
                    st.session_state[f"result_{ticker}"] = result
                    st.success("✅ 分析完成！")
                except Exception as e:
                    st.error(f"流水线出错：{e}")

    result = st.session_state.get(f"result_{ticker}")

    # ── Tabs ─────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(["📈 财务指标", "🎯 大师评分", "⚔️ 辩论摘要", "📋 估值结论"])

    # ── Tab 1: 财务趋势 ───────────────────────────────────────
    with tab1:
        fin_data = (result or {}).get("financial_data", [])
        if fin_data:
            df = pd.DataFrame(fin_data)
            df["period"] = pd.to_datetime(df["period"])
            df = df.sort_values("period")

            fig = go.Figure()
            if "revenue" in df.columns:
                fig.add_trace(go.Bar(x=df["period"], y=df["revenue"].astype(float),
                                     name="营业收入", marker_color="#4C78A8"))
            if "net_profit" in df.columns:
                fig.add_trace(go.Bar(x=df["period"], y=df["net_profit"].astype(float),
                                     name="净利润", marker_color="#72B7B2"))
            fig.update_layout(title="营收 & 净利润趋势", barmode="group", height=350)
            st.plotly_chart(fig, use_container_width=True)

            col_a, col_b = st.columns(2)
            with col_a:
                fig2 = px.line(df, x="period", y="gross_margin", title="毛利率趋势 (%)",
                               markers=True)
                fig2.update_traces(line_color="#E45756")
                st.plotly_chart(fig2, use_container_width=True)
            with col_b:
                fig3 = px.line(df, x="period", y="roe", title="ROE 趋势 (%)", markers=True)
                fig3.update_traces(line_color="#54A24B")
                st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("运行分析后将显示财务趋势图表")
            # 展示示例数据
            _show_sample_financials()

    # ── Tab 2: 大师评分 ───────────────────────────────────────
    with tab2:
        signals = (result or {}).get("master_signals", [])
        if signals:
            master_names = ["Warren Buffett", "Ben Graham", "Aswath Damodaran",
                            "Charlie Munger", "Philip Fisher"]
            cols = st.columns(min(len(signals), 5))
            for i, sig in enumerate(signals[:5]):
                signal_val = sig.get("signal", "neutral")
                confidence = sig.get("confidence", 0)
                reasoning = sig.get("reasoning", "")
                name = master_names[i] if i < len(master_names) else f"大师{i+1}"
                with cols[i]:
                    st.markdown(f"**{name.split()[-1]}**")
                    st.markdown(f"{_signal_color(signal_val)} **{signal_val.upper()}**")
                    st.caption(_confidence_bar(confidence))

            st.divider()
            for i, sig in enumerate(signals):
                name = master_names[i] if i < len(master_names) else f"大师{i+1}"
                signal_val = sig.get("signal", "neutral")
                with st.expander(f"{_signal_color(signal_val)} {name} — {signal_val.upper()} ({sig.get('confidence',0):.0f}%)"):
                    st.markdown(sig.get("reasoning", "暂无分析"))
        else:
            st.info("运行估值流水线后将显示五位大师的评分卡片")

    # ── Tab 3: 辩论摘要 ───────────────────────────────────────
    with tab3:
        debate = (result or {}).get("debate_result", {})
        if debate:
            stance = debate.get("final_stance", "neutral")
            confidence = debate.get("confidence", 50)
            st.markdown(f"### 裁判结论：{_signal_color(stance)} **{stance.upper()}**  置信度 {confidence:.0f}%")
            st.markdown("**裁判分析：**")
            st.markdown(debate.get("judge_summary", ""))

            rounds = debate.get("rounds", [])
            if rounds:
                st.divider()
                st.markdown(f"**辩论共 {len(rounds)} 轮**")
                for r in rounds:
                    with st.expander(f"第 {r.get('round_num', '?')} 轮"):
                        col_b, col_s = st.columns(2)
                        with col_b:
                            st.markdown("🟢 **多头**")
                            st.markdown(r.get("bull_argument", ""))
                        with col_s:
                            st.markdown("🔴 **空头**")
                            st.markdown(r.get("bear_argument", ""))
        else:
            st.info("运行估值流水线后将显示多空辩论记录")

    # ── Tab 4: 估值结论 ───────────────────────────────────────
    with tab4:
        report = (result or {}).get("final_report", {})
        if report:
            v_low = float(report.get("valuation_low", 0))
            v_mid = float(report.get("valuation_mid", 0))
            v_high = float(report.get("valuation_high", 0))

            col1, col2, col3 = st.columns(3)
            col1.metric("低情景", f"{v_low:,.0f}", help="蒙特卡洛 P25")
            col2.metric("中情景", f"{v_mid:,.0f}", delta=f"相对低情景 +{v_mid-v_low:,.0f}", help="蒙特卡洛 P50")
            col3.metric("高情景", f"{v_high:,.0f}", help="蒙特卡洛 P75")

            # 估值区间图
            if v_mid > 0:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=[v_low, v_mid, v_high],
                    y=["估值", "估值", "估值"],
                    mode="markers+lines",
                    marker=dict(size=[12, 18, 12], color=["#72B7B2", "#4C78A8", "#72B7B2"]),
                    line=dict(color="#4C78A8", width=3),
                    text=[f"低 {v_low:,.0f}", f"中 {v_mid:,.0f}", f"高 {v_high:,.0f}"],
                    textposition="top center",
                ))
                fig.update_layout(title="估值区间（蒙特卡洛）", height=200,
                                  showlegend=False, yaxis=dict(visible=False))
                st.plotly_chart(fig, use_container_width=True)

            st.divider()
            col_bull, col_bear = st.columns(2)
            with col_bull:
                st.markdown("#### 🟢 多头论据")
                for a in report.get("bull_arguments", []):
                    st.markdown(f"- {a[:200]}")
            with col_bear:
                st.markdown("#### 🔴 空头论据")
                for a in report.get("bear_arguments", []):
                    st.markdown(f"- {a[:200]}")

            st.divider()
            st.markdown("#### 关键假设")
            for a in report.get("key_assumptions", []):
                st.caption(f"• {a}")

            # Risk
            risk = (result or {}).get("risk_assessment", {})
            if risk:
                level = risk.get("risk_level", "medium")
                color = {"low": "green", "medium": "orange", "high": "red"}.get(level, "grey")
                st.markdown(f"#### 风险评级：:{color}[**{level.upper()}**]")
                for r in risk.get("risks", [])[:5]:
                    st.caption(f"⚠ {r}")
        else:
            st.info("运行估值流水线后将显示最终估值报告")


def _show_sample_financials():
    """Show sample financial data as placeholder."""
    sample = pd.DataFrame({
        "年份": [2020, 2021, 2022, 2023, 2024],
        "营业收入(亿)": [94.9, 106.2, 127.8, 150.6, 159.4],
        "净利润(亿)": [46.7, 52.4, 62.7, 71.2, 74.7],
        "毛利率(%)": [91.0, 91.3, 91.5, 91.5, 91.8],
        "ROE(%)": [31.9, 31.7, 33.3, 35.1, 34.2],
    })
    st.caption("📊 示例数据（贵州茅台历史数据）")
    st.dataframe(sample, use_container_width=True, hide_index=True)
