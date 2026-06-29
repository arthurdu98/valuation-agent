import streamlit as st
from datetime import date
from src.data.company_manager import CompanyManager
from src.data.industry.baijiu import BaijiuPlugin
from src.data.industry.internet import InternetPlugin
from src.data.industry.tcm import TCMPlugin
from src.data.industry.toy import ToyPlugin

INDUSTRY_PLUGINS = {
    "白酒": BaijiuPlugin(),
    "互联网": InternetPlugin(),
    "中药": TCMPlugin(),
    "潮玩": ToyPlugin(),
}

def render_metric_input():
    st.header("📝 行业指标录入")

    cm = CompanyManager()
    companies = cm.get_tracked_companies()

    selected = st.selectbox("选择公司", [f"{c.name} ({c.ticker}) - {c.industry}" for c in companies])

    if selected:
        ticker = selected.split("(")[1].split(")")[0]
        company = next((c for c in companies if c.ticker == ticker), None)

        if company and company.industry in INDUSTRY_PLUGINS:
            plugin = INDUSTRY_PLUGINS[company.industry]
            st.subheader(f"{company.industry} 行业指标")

            with st.form("metric_form"):
                record_date = st.date_input("记录日期", value=date.today())

                values = {}
                for metric in plugin.metrics:
                    mode_icon = {"auto": "🤖", "semi_auto": "📷", "manual": "✍️"}.get(metric.collection_mode.value, "")
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        val = st.number_input(
                            f"{mode_icon} {metric.display_name}",
                            help=metric.description,
                            value=0.0,
                            key=f"metric_{metric.name}",
                        )
                        values[metric.name] = val
                    with col2:
                        st.caption(metric.collection_mode.value)

                submitted = st.form_submit_button("💾 保存指标")
                if submitted:
                    non_zero = {k: v for k, v in values.items() if v != 0}
                    if non_zero:
                        st.success(f"已记录 {len(non_zero)} 个指标 ({record_date})")
                        st.json(non_zero)
                    else:
                        st.warning("请至少填写一个指标")

            # Screenshot upload for semi-auto
            st.divider()
            st.subheader("📷 截图识别（半自动）")
            uploaded = st.file_uploader("上传批价/数据截图", type=["png", "jpg", "jpeg"])
            if uploaded:
                st.image(uploaded, caption="已上传截图")
                st.info("LLM 视觉识别功能将在接入后自动提取数据预填表单")
        else:
            st.info(f"暂无 {company.industry if company else '未知'} 行业的指标配置")
