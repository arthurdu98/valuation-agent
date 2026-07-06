"""Report export endpoints (markdown / PDF download)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from src.api.deps import get_run_registry
from src.api.run_registry import RunRegistry
from src.schemas import ValuationReport
from src.export import render_markdown

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _get_report_and_name(run_id: str, registry: RunRegistry) -> tuple[ValuationReport, str]:
    """Extract the ValuationReport from a completed run."""
    record = registry.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run 不存在")
    if record.result is None:
        raise HTTPException(status_code=409, detail="run 尚未完成")

    report_dict = record.result.get("final_report")
    if not report_dict:
        raise HTTPException(status_code=404, detail="该 run 未生成估值报告")

    # Reconstruct the Pydantic model from the stored dict.
    report = ValuationReport(**report_dict)
    return report, record.company_name


@router.get("/{run_id}/markdown")
def download_markdown(
    run_id: str,
    registry: RunRegistry = Depends(get_run_registry),
):
    report, company_name = _get_report_and_name(run_id, registry)
    md = render_markdown(report, company_name)
    filename = f"valuation_{report.ticker}_{run_id[:8]}.md"
    return PlainTextResponse(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{run_id}/pdf")
def download_pdf(
    run_id: str,
    registry: RunRegistry = Depends(get_run_registry),
):
    """PDF export — requires weasyprint. Returns 501 if not installed."""
    report, company_name = _get_report_and_name(run_id, registry)

    try:
        from src.export import export_pdf
    except Exception:
        raise HTTPException(status_code=501, detail="PDF 导出需安装 weasyprint")

    import tempfile
    from pathlib import Path
    from fastapi.responses import FileResponse

    tmp = Path(tempfile.mktemp(suffix=".pdf"))
    try:
        export_pdf(report, tmp, company_name)
        return FileResponse(
            path=str(tmp),
            media_type="application/pdf",
            filename=f"valuation_{report.ticker}_{run_id[:8]}.pdf",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))
