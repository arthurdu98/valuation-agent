"""Industry comparison page — competitor metrics, radar chart, valuation matrix."""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from src.data.company_manager import CompanyManager


_SIGNAL_EMOJI = {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}

# Static comparable data for the 6 pre-configured companies
# In production these come from AKShare/yfinance via DataCollector
_STATIC_METRICS: dict[str, dict] = {
    "600519": {"name": "贵州茅台", "pe": 25.1, "pb": 8.6, "ps": 10.2,
               "gross_margin": 91.8, "roe": 34.2, "revenue_growth": 5.9,
               "net_margin": 46.9, "debt_ratio": 0.34, "market_cap_bn": 3200},
    "000858": {"name": "五粮液",   "pe": 18.3, "pb": 5.1, "ps": 7.4,
               "gross_margin": 77.5, "roe": 33.5, "revenue_growth": 8.2,
               "net_margin": 35.1, "debt_ratio": 0.28, "market_cap_bn": 2100},
    "000568": {"name": "泸州老窖", "pe": 16.2, "pb": 4.8, "ps": 6.1,
               "gross_margin": 86.6, "roe": 22.7, "revenue_growth": -3.1,
               "net_margin": 38.4, "debt_ratio": 0.31, "market_cap_bn": 1450},
    "600436": {"name": "片仔癀",   "pe": 42.5, "pb": 12.3, "ps": 15.1,
               "gross_margin": 68.2, "roe": 28.6, "revenue_growth": 12.4,
               "net_margin": 25.7, "debt_ratio": 0.22, "market_cap_bn": 580},
    "9992":   {"name": "泡泡玛特", "pe": 14.9, "pb": 6.2, "ps": 5.3,
               "gross_margin": 72.1, "roe": 77.5, "revenue_growth": 185.0,
               "net_margin": 35.1, "debt_ratio": 0.29, "market_cap_bn": 2200},
    "GOOGL":  {"name": "Alphabet", "pe": 21.4, "pb": 6.8, "ps": 6.3,
               "gross_margin": 57.9, "roe": 31.2, "revenue_growth": 14.3,
               "net_margin": 28.5, "debt_ratio": 0.14, "market_cap_bn": 22000},
}


def render_industry_compare():
    st.header("行业对比分析")

    cm = CompanyManager()
    companies = cm.get_tracked_companies()
    if not companies:
        st.warning("暂无追踪公司")
        return

    industries = sorted(set(c.industry for c in companies))
    industries.insert(0, "全部")
    selected_industry = st.selectbox("筛选行业", industries)

    if selected_industry == "全部":
        filtered = companies
    else:
        filtered = [c for c in companies if c.industry == selected_industry]

    tickers = [c.ticker for c in filtered]
    rows = []
    for c in filtered:
        m = _STATIC_METRICS.get(c.ticker, {})
        rows.append({
            "公司": c.name,
            "代码": c.ticker,
            "行业": c.industry,
            "市场": c.market.value.upper(),
            "PE": m.get("pe", "—"),
            "PB": m.get("pb", "—"),
            "毛利率(%)": m.get("gross_margin", "—"),
            "ROE(%)": m.get("roe", "—"),
            "营收增速(%)": m.get("revenue_growth", "—"),
            "净利率(%)": m.get("net_margin", "—"),
            "市值(亿)": m.get("market_cap_bn", "—"),
        })
    df = pd.DataFrame(rows)

    # ── 汇总表 ──────────────────────────────────────────────
    st.subheader(f"📊 核心指标对比  ({len(filtered)} 家)")
    st.dataframe(
        df.style.background_gradient(
            subset=["毛利率(%)", "ROE(%)", "营收增速(%)"], cmap="RdYlGn"
        ).format(precision=1),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ── 估值倍数对比 ────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("估值倍数对比 (PE / PB / PS)")
        valid = [(c.ticker, _STATIC_METRICS[c.ticker]) for c in filtered if c.ticker in _STATIC_METRICS]
        if valid:
            names = [_STATIC_METRICS[t]["name"] for t, _ in valid]
            pe_vals = [d["pe"] for _, d in valid]
            pb_vals = [d["pb"] for _, d in valid]
            ps_vals = [d["ps"] for _, d in valid]

            fig = go.Figure()
            fig.add_trace(go.Bar(name="PE", x=names, y=pe_vals, marker_color="#4C78A8"))
            fig.add_trace(go.Bar(name="PB", x=names, y=pb_vals, marker_color="#72B7B2"))
            fig.add_trace(go.Bar(name="PS", x=names, y=ps_vals, marker_color="#F58518"))
            fig.update_layout(barmode="group", height=380, margin=dict(t=20))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("盈利能力对比 (毛利率 / ROE / 净利率)")
        if valid:
            gm_vals = [_STATIC_METRICS[t]["gross_margin"] for t, _ in valid]
            roe_vals = [_STATIC_METRICS[t]["roe"] for t, _ in valid]
            nm_vals = [_STATIC_METRICS[t]["net_margin"] for t, _ in valid]

            fig2 = go.Figure()
            fig2.add_trace(go.Bar(name="毛利率%", x=names, y=gm_vals, marker_color="#54A24B"))
            fig2.add_trace(go.Bar(name="ROE%", x=names, y=roe_vals, marker_color="#EECA3B"))
            fig2.add_trace(go.Bar(name="净利率%", x=names, y=nm_vals, marker_color="#B279A2"))
            fig2.update_layout(barmode="group", height=380, margin=dict(t=20))
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── 雷达图对比（选最多4家） ────────────────────────────
    st.subheader("🕸 雷达图对比")
    radar_options = [c.name for c in filtered if c.ticker in _STATIC_METRICS]
    selected_radar = st.multiselect("选择公司（最多4家）", radar_options,
                                    default=radar_options[:min(4, len(radar_options))])

    if selected_radar:
        categories = ["毛利率", "ROE", "净利率", "营收增速", "估值(低PE更好)"]
        fig_radar = go.Figure()

        for c in filtered:
            if c.name not in selected_radar:
                continue
            m = _STATIC_METRICS.get(c.ticker, {})
            # normalize to 0-100 scale for radar
            values = [
                min(m.get("gross_margin", 0), 100),
                min(m.get("roe", 0), 100),
                min(m.get("net_margin", 0) * 1.5, 100),
                min(max(m.get("revenue_growth", 0) + 20, 0), 100),
                max(100 - m.get("pe", 50) * 1.5, 0),
            ]
            values.append(values[0])  # close the polygon
            cats = categories + [categories[0]]

            fig_radar.add_trace(go.Scatterpolar(
                r=values, theta=cats, fill="toself",
                name=c.name, opacity=0.7,
            ))

        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True, height=480,
        )
        st.plotly_chart(fig_radar, use_container_width=True)
        st.caption("注：雷达图已归一化，PE 越低得分越高（估值越便宜）")

    st.divider()

    # ── 营收增速排名 ────────────────────────────────────────
    st.subheader("📈 营收增速排名")
    growth_data = [
        {"公司": _STATIC_METRICS[c.ticker]["name"],
         "营收增速(%)": _STATIC_METRICS[c.ticker]["revenue_growth"]}
        for c in filtered if c.ticker in _STATIC_METRICS
    ]
    if growth_data:
        df_growth = pd.DataFrame(growth_data).sort_values("营收增速(%)", ascending=True)
        colors = ["#54A24B" if v >= 0 else "#E45756" for v in df_growth["营收增速(%)"]]
        fig_g = go.Figure(go.Bar(
            x=df_growth["营收增速(%)"], y=df_growth["公司"],
            orientation="h", marker_color=colors,
            text=df_growth["营收增速(%)"].apply(lambda x: f"{x:+.1f}%"),
            textposition="outside",
        ))
        fig_g.update_layout(height=max(250, len(growth_data) * 55), margin=dict(l=20, r=80))
        st.plotly_chart(fig_g, use_container_width=True)
        st.caption("数据来源：静态示例数据，接入数据源后将实时更新")
