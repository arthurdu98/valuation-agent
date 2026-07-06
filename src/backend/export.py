"""Report rendering and export utilities.

Migrated from src/ui/export.py so the API layer can import it after Streamlit
removal. Interface and behavior are unchanged.
"""

from __future__ import annotations

from pathlib import Path

from src.backend.schemas import ValuationReport


def render_markdown(report: ValuationReport, company_name: str = "") -> str:
    """Render a valuation report to Markdown."""
    title = company_name or report.ticker
    return f"""# 估值分析报告：{title}

## 估值区间
- 低位: {report.valuation_low}
- 中枢: {report.valuation_mid}
- 高位: {report.valuation_high}
- PE 分位: {report.pe_quantile:.1%}

## 看多论据
{_render_list(report.bull_arguments)}

## 看空论据
{_render_list(report.bear_arguments)}

## 关键假设
{_render_list(report.key_assumptions)}

## 敏感因素
```json
{report.sensitivity_factors}
```

## 竞对对比
```json
{report.competitor_comparison}
```
"""


def export_markdown(report: ValuationReport, path: str | Path, company_name: str = "") -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(report, company_name), encoding="utf-8")
    return output


def export_pdf(report: ValuationReport, path: str | Path, company_name: str = "") -> Path:
    """Export a report as PDF via weasyprint when installed."""
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError("weasyprint is required for PDF export") from exc

    markdown = render_markdown(report, company_name)
    html = "<pre style='font-family: sans-serif; white-space: pre-wrap'>" + markdown + "</pre>"
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html).write_pdf(str(output))
    return output


def _render_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- 暂无"
