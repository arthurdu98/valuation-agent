import streamlit as st
from src.data.company_manager import CompanyManager


def render_industry_compare():
    st.header("行业对比分析")
    cm = CompanyManager()
    companies = cm.get_tracked_companies()

    industries = list(set(c.industry for c in companies))
    selected_industry = st.selectbox("选择行业", industries)

    if selected_industry:
        industry_companies = [c for c in companies if c.industry == selected_industry]

        st.subheader(f"{selected_industry} - {len(industry_companies)} 家公司")

        # Comparison table placeholder
        import pandas as pd
        data = []
        for c in industry_companies:
            data.append({
                "公司": c.name,
                "代码": c.ticker,
                "市场": c.market.value,
                "PE": "待采集",
                "ROE": "待采集",
                "营收增速": "待采集",
            })
        if data:
            st.dataframe(pd.DataFrame(data), use_container_width=True)

        st.subheader("估值对比矩阵")
        st.info("数据采集后将展示 PE/PB/PS 横向对比和雷达图")
