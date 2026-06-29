import streamlit as st
from datetime import datetime
from decimal import Decimal

from src.schemas import ValuationReport
from src.ui.export import render_markdown

def render_export():
    st.header("📋 估值报告导出")

    st.info("选择一份已确认的估值报告进行导出")

    # Placeholder - will connect to DB
    reports = [
        {"ticker": "600519", "name": "贵州茅台", "date": "2024-01-15", "status": "待生成"},
    ]

    selected = st.selectbox("选择报告", [f"{r['name']} - {r['date']} ({r['status']})" for r in reports])

    export_format = st.radio("导出格式", ["Markdown", "PDF"], horizontal=True)

    if st.button("导出报告"):
        if export_format == "Markdown":
            report = ValuationReport(
                ticker=reports[0]["ticker"],
                valuation_low=Decimal("0"),
                valuation_mid=Decimal("0"),
                valuation_high=Decimal("0"),
                pe_quantile=0.5,
                bull_arguments=["待生成"],
                bear_arguments=["待生成"],
                key_assumptions=[f"导出日期: {datetime.now().strftime('%Y-%m-%d')}"],
            )
            report_md = render_markdown(report, reports[0]["name"])
            st.download_button(
                label="📥 下载 Markdown",
                data=report_md,
                file_name=f"valuation_{reports[0]['ticker']}_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown",
            )
        else:
            st.info("PDF 导出需要安装 weasyprint 依赖")

    st.divider()
    st.subheader("历史报告")
    st.caption("估值报告将在流水线运行并确认后出现在这里")
