import streamlit as st
from src.data.company_manager import CompanyManager


def render_home():
    st.header("追踪公司概览")
    cm = CompanyManager()
    companies = cm.get_tracked_companies()

    # Group by industry
    industries = {}
    for c in companies:
        industries.setdefault(c.industry, []).append(c)

    for industry, comps in industries.items():
        st.subheader(f"🏭 {industry}")
        cols = st.columns(len(comps))
        for i, comp in enumerate(comps):
            with cols[i]:
                st.metric(label=comp.name, value=comp.ticker)
                st.caption(f"市场: {comp.market.value}")
                if comp.competitors:
                    st.caption(f"竞对: {', '.join(comp.competitors[:3])}")

    st.divider()
    st.subheader("➕ 添加公司")
    with st.form("add_company"):
        ticker = st.text_input("股票代码")
        name = st.text_input("公司名称")
        market = st.selectbox("市场", ["a_share", "hk", "us"])
        industry = st.text_input("行业")
        if st.form_submit_button("添加"):
            if ticker and name:
                st.success(f"已添加 {name} ({ticker})")
            else:
                st.warning("请填写代码和名称")
