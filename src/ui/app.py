import streamlit as st

st.set_page_config(page_title="估值监控系统", layout="wide", page_icon="📊")

st.title("📊 多行业估值监控与智能体辩证分析系统")
st.sidebar.title("导航")
page = st.sidebar.radio("选择页面", ["首页", "公司详情", "行业对比", "指标录入", "报告导出"])

if page == "首页":
    from src.ui.pages.home import render_home
    render_home()
elif page == "公司详情":
    from src.ui.pages.company_detail import render_company_detail
    render_company_detail()
elif page == "行业对比":
    from src.ui.pages.industry_compare import render_industry_compare
    render_industry_compare()
elif page == "指标录入":
    from src.ui.pages.metric_input import render_metric_input
    render_metric_input()
elif page == "报告导出":
    from src.ui.pages.export import render_export
    render_export()
