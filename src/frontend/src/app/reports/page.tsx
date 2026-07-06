"use client";

import { useState } from "react";
import { useRunStore } from "@/stores/runStore";
import { api } from "@/lib/api";
import { Card, CardBody, CardHeader } from "@/components/common/Card";

export default function ReportsPage() {
  const runs = useRunStore((s) => s.runs);
  const completedRuns = Object.values(runs).filter(
    (r) => r.finished && !r.error,
  );

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">估值报告导出</h1>

      {completedRuns.length === 0 ? (
        <Card>
          <CardBody>
            <div className="text-center py-8 text-muted-foreground">
              <p className="text-lg mb-2">暂无已完成的分析</p>
              <p className="text-sm">
                请先在{" "}
                <a href="/" className="text-primary underline">
                  公司详情
                </a>{" "}
                页面运行估值分析，完成后即可在此导出报告。
              </p>
            </div>
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-4">
          {completedRuns.map((run) => (
            <ReportCard
              key={run.runId}
              runId={run.runId!}
              ticker={run.ticker!}
              companyName={run.ticker!}
            />
          ))}
        </div>
      )}

      <Card className="mt-8">
        <CardHeader title="导出说明" />
        <CardBody>
          <ul className="text-sm text-muted-foreground space-y-2 list-disc list-inside">
            <li>Markdown 格式：包含估值区间、多空论据、关键假设、敏感因素、竞对对比</li>
            <li>PDF 格式：需后端安装 weasyprint 依赖（当前可能不可用）</li>
            <li>报告内容来自 L1-L5 流水线最终输出</li>
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}

function ReportCard({
  runId,
  ticker,
  companyName,
}: {
  runId: string;
  ticker: string;
  companyName: string;
}) {
  const [downloading, setDownloading] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  const downloadMd = async () => {
    setDownloading(true);
    try {
      const url = api.reportMarkdownUrl(runId);
      const res = await fetch(url);
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `valuation_${ticker}_${runId.slice(0, 8)}.md`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      alert(`下载失败: ${(e as Error).message}`);
    } finally {
      setDownloading(false);
    }
  };

  const downloadPdf = async () => {
    setPdfError(null);
    try {
      const url = api.reportPdfUrl(runId);
      const res = await fetch(url);
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        setPdfError(body.detail ?? "PDF 导出失败");
        return;
      }
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `valuation_${ticker}_${runId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      setPdfError((e as Error).message);
    }
  };

  return (
    <Card>
      <CardBody>
        <div className="flex items-center justify-between">
          <div>
            <div className="font-medium">{companyName}</div>
            <div className="text-xs text-muted-foreground mt-0.5">
              Run ID: {runId.slice(0, 12)}…
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={downloadMd}
              disabled={downloading}
              className="bg-primary text-primary-foreground px-3 py-1.5 rounded-md text-sm font-medium disabled:opacity-50 hover:opacity-90 transition"
            >
              {downloading ? "下载中…" : "📄 Markdown"}
            </button>
            <button
              onClick={downloadPdf}
              className="border border-border text-foreground px-3 py-1.5 rounded-md text-sm hover:bg-muted transition"
            >
              📑 PDF
            </button>
          </div>
        </div>
        {pdfError && (
          <p className="text-xs text-destructive mt-2">{pdfError}</p>
        )}
      </CardBody>
    </Card>
  );
}
