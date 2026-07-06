"use client";

import { use } from "react";
import { useCompany, useRunResult } from "@/lib/queries";
import { useRunStore } from "@/stores/runStore";
import { Card, CardBody, CardHeader } from "@/components/common/Card";
import { MetricTile } from "@/components/common/MetricTile";
import { RunControls } from "@/components/pipeline/RunControls";
import { StageTimeline } from "@/components/pipeline/StageTimeline";
import { ResultTabs } from "@/components/company/ResultTabs";

export default function CompanyDetailPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = use(params);
  const { data: company, isLoading, error } = useCompany(ticker);
  const run = useRunStore((s) => s.runs[ticker]);
  const { data: result } = useRunResult(
    run?.runId ?? null,
    !!run?.finished && !run?.error,
  );

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 w-48 bg-muted rounded" />
        <div className="h-32 bg-muted rounded-lg" />
      </div>
    );
  }

  if (error || !company) {
    return <p className="text-destructive">公司不存在或加载失败</p>;
  }

  return (
    <div className="space-y-6">
      {/* Header metrics */}
      <div>
        <h1 className="text-2xl font-bold mb-4">{company.name}</h1>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricTile label="代码" value={company.ticker} />
          <MetricTile label="行业" value={company.industry} />
          <MetricTile label="市场" value={company.market.toUpperCase()} />
          <MetricTile label="竞争对手" value={company.competitors.length} />
        </div>
      </div>

      {/* Run controls */}
      <Card>
        <CardHeader title="▶ 运行估值分析" subtitle="L1-L5 流水线，约 2-4 分钟" />
        <CardBody>
          <RunControls ticker={ticker} />
        </CardBody>
      </Card>

      {/* Live progress (only when a run is active or just finished) */}
      {run && (
        <Card>
          <CardBody>
            <StageTimeline run={run} />
            {run.error && (
              <p className="text-destructive text-sm mt-3">❌ {run.error}</p>
            )}
          </CardBody>
        </Card>
      )}

      {/* Results */}
      {result && (
        <Card>
          <CardHeader title="分析结果" />
          <CardBody>
            <ResultTabs result={result} />
          </CardBody>
        </Card>
      )}
    </div>
  );
}
