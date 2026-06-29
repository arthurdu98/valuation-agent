import streamlit as st
from src.data.company_manager import CompanyManager


def render_company_detail():
    st.header("公司详情分析")
    cm = CompanyManager()
    companies = cm.get_tracked_companies()

    selected = st.selectbox("选择公司", [f"{c.name} ({c.ticker})" for c in companies])

    if selected:
        ticker = selected.split("(")[1].rstrip(")")
        company = next((c for c in companies if c.ticker == ticker), None)

        if company:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("行业", company.industry)
            with col2:
                st.metric("市场", company.market.value.upper())
            with col3:
                st.metric("竞争对手", len(company.competitors))

            # Tabs for different views
            tab1, tab2, tab3, tab4 = st.tabs(["📈 财务指标", "🎯 大师评分", "⚔️ 辩论摘要", "📋 估值结论"])

            with tab1:
                st.info("财务数据将在数据采集后展示")
                st.caption("PE分位带 | 营收趋势 | ROE走势 | 现金流")

            with tab2:
                st.info("运行估值流水线后展示大师评分卡片")
                masters = ["巴菲特", "芒格", "格雷厄姆", "达摩达兰", "费雪"]
                cols = st.columns(5)
                for i, m in enumerate(masters):
                    with cols[i]:
                        st.markdown(f"**{m}**")
                        st.caption("待分析")

            with tab3:
                st.info("辩论结果将在流水线运行后展示")

            with tab4:
                st.info("最终估值报告待生成")
