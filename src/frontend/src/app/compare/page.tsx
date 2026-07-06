"use client";

import { useMemo, useState } from "react";
import { useCompare, useIndustries } from "@/lib/queries";
import { Card, CardBody, CardHeader } from "@/components/common/Card";
import { GroupedBarChart } from "@/components/charts/GroupedBarChart";
import { RadarChart } from "@/components/charts/RadarChart";
import { HorizontalBarChart } from "@/components/charts/HorizontalBarChart";
import type { ComparisonRow } from "@/lib/types";

export default function ComparePage() {
  const [industry, setIndustry] = useState("全部");
  const { data: industries } = useIndustries();
  const { data, isLoading, error } = useCompare(industry);
  const rows = data?.rows ?? [];

  const withMetrics = rows.filter((r) => r.pe != null);
  const [selectedRadar, setSelectedRadar] = useState<string[]>([]);

  // Default radar selection = first 4 with metrics.
  const radarNames = useMemo(() => {
    if (selectedRadar.length > 0) return selectedRadar;
    return withMetrics.slice(0, 4).map((r) => r.name);
  }, [selectedRadar, withMetrics]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">行业对比分析</h1>
        <select
          value={industry}
          onChange={(e) => {
            setIndustry(e.target.value);
            setSelectedRadar([]);
          }}
          className="border border-border rounded-md px-3 py-1.5 text-sm bg-card"
        >
          <option value="全部">全部行业</option>
          {industries?.map((ind) => (
            <option key={ind} value={ind}>
              {ind}
            </option>
          ))}
        </select>
      </div>

      {isLoading && <p className="text-muted-foreground">加载中…</p>}
      {error && <p className="text-destructive">加载失败：{(error as Error).message}</p>}

      {rows.length > 0 && (
        <div className="space-y-6">
          <Card>
            <CardHeader title={`核心指标对比 (${rows.length} 家)`} />
            <CardBody className="overflow-x-auto p-0">
              <ComparisonTable rows={rows} />
            </CardBody>
          </Card>

          {withMetrics.length > 0 && (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader title="估值倍数对比 (PE / PB / PS)" />
                  <CardBody>
                    <GroupedBarChart
                      categories={withMetrics.map((r) => r.name)}
                      series={[
                        { name: "PE", data: withMetrics.map((r) => r.pe) },
                        { name: "PB", data: withMetrics.map((r) => r.pb) },
                        { name: "PS", data: withMetrics.map((r) => r.ps) },
                      ]}
                    />
                  </CardBody>
                </Card>
                <Card>
                  <CardHeader title="盈利能力对比 (毛利率 / ROE / 净利率)" />
                  <CardBody>
                    <GroupedBarChart
                      categories={withMetrics.map((r) => r.name)}
                      series={[
                        { name: "毛利率%", data: withMetrics.map((r) => r.gross_margin) },
                        { name: "ROE%", data: withMetrics.map((r) => r.roe) },
                        { name: "净利率%", data: withMetrics.map((r) => r.net_margin) },
                      ]}
                    />
                  </CardBody>
                </Card>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader title="🕸 雷达图对比" subtitle="最多选 4 家" />
                  <CardBody>
                    <div className="flex flex-wrap gap-2 mb-3">
                      {withMetrics.map((r) => {
                        const active = radarNames.includes(r.name);
                        return (
                          <button
                            key={r.ticker}
                            onClick={() => {
                              const base = selectedRadar.length ? selectedRadar : radarNames;
                              if (active) {
                                setSelectedRadar(base.filter((n) => n !== r.name));
                              } else if (base.length < 4) {
                                setSelectedRadar([...base, r.name]);
                              }
                            }}
                            className={`text-xs px-2 py-1 rounded border ${
                              active
                                ? "bg-primary text-primary-foreground border-primary"
                                : "bg-card border-border text-muted-foreground"
                            }`}
                          >
                            {r.name}
                          </button>
                        );
                      })}
                    </div>
                    <RadarChart
                      indicators={[
                        { name: "毛利率", max: 100 },
                        { name: "ROE", max: 100 },
                        { name: "净利率", max: 60 },
                        { name: "营收增速", max: 200 },
                        { name: "估值(低PE优)", max: 100 },
                      ]}
                      series={withMetrics
                        .filter((r) => radarNames.includes(r.name))
                        .map((r) => ({
                          name: r.name,
                          values: [
                            r.gross_margin ?? 0,
                            r.roe ?? 0,
                            r.net_margin ?? 0,
                            Math.max(r.revenue_growth ?? 0, 0),
                            Math.max(100 - (r.pe ?? 0), 0),
                          ],
                        }))}
                    />
                  </CardBody>
                </Card>

                <Card>
                  <CardHeader title="营收增速排名" />
                  <CardBody>
                    <HorizontalBarChart
                      categories={[...withMetrics]
                        .sort((a, b) => (a.revenue_growth ?? 0) - (b.revenue_growth ?? 0))
                        .map((r) => r.name)}
                      values={[...withMetrics]
                        .sort((a, b) => (a.revenue_growth ?? 0) - (b.revenue_growth ?? 0))
                        .map((r) => r.revenue_growth ?? 0)}
                      signColors
                      suffix="%"
                    />
                  </CardBody>
                </Card>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function ComparisonTable({ rows }: { rows: ComparisonRow[] }) {
  const cols: { key: keyof ComparisonRow; label: string; grad?: boolean }[] = [
    { key: "name", label: "公司" },
    { key: "ticker", label: "代码" },
    { key: "market", label: "市场" },
    { key: "pe", label: "PE" },
    { key: "pb", label: "PB" },
    { key: "gross_margin", label: "毛利率%", grad: true },
    { key: "roe", label: "ROE%", grad: true },
    { key: "revenue_growth", label: "营收增速%", grad: true },
    { key: "net_margin", label: "净利率%" },
    { key: "market_cap_bn", label: "市值(亿)" },
  ];

  // Compute min/max for gradient columns.
  const ranges: Record<string, { min: number; max: number }> = {};
  for (const c of cols.filter((c) => c.grad)) {
    const vals = rows.map((r) => r[c.key] as number).filter((v) => v != null);
    ranges[c.key] = { min: Math.min(...vals), max: Math.max(...vals) };
  }

  const gradColor = (key: string, v: number | null) => {
    if (v == null || !ranges[key]) return undefined;
    const { min, max } = ranges[key];
    if (max === min) return undefined;
    const t = (v - min) / (max - min); // 0..1
    // red -> yellow -> green
    const hue = t * 120; // 0=red,120=green
    return `hsl(${hue}, 70%, 90%)`;
  };

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-border text-muted-foreground">
          {cols.map((c) => (
            <th key={c.key} className="text-left font-medium px-4 py-2.5 whitespace-nowrap">
              {c.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.ticker} className="border-b border-border/50 hover:bg-muted/40">
            {cols.map((c) => {
              const v = r[c.key];
              const bg = c.grad ? gradColor(c.key, v as number | null) : undefined;
              return (
                <td key={c.key} className="px-4 py-2.5 whitespace-nowrap" style={bg ? { background: bg } : undefined}>
                  {v == null ? "—" : typeof v === "number" ? v.toFixed(1) : v}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
