"use client";

import { useState } from "react";
import type { RunResult } from "@/lib/types";
import { SignalBadge } from "@/components/common/SignalBadge";
import { ConfidenceBar } from "@/components/common/ConfidenceBar";
import { MetricTile } from "@/components/common/MetricTile";
import { GroupedBarChart } from "@/components/charts/GroupedBarChart";
import { LineChart } from "@/components/charts/LineChart";
import { EChart } from "@/components/charts/EChart";
import type { EChartsOption } from "echarts";

const TABS = ["财务指标", "大师评分", "辩论摘要", "估值结论"] as const;
type Tab = (typeof TABS)[number];

export function ResultTabs({ result }: { result: RunResult }) {
  const [tab, setTab] = useState<Tab>("财务指标");

  return (
    <div>
      <div className="flex gap-1 border-b border-border mb-5">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "财务指标" && <FinancialsTab result={result} />}
      {tab === "大师评分" && <MastersTab result={result} />}
      {tab === "辩论摘要" && <DebateTab result={result} />}
      {tab === "估值结论" && <ValuationTab result={result} />}
    </div>
  );
}

function FinancialsTab({ result }: { result: RunResult }) {
  const fin = result.financial_data ?? [];
  // financial_data periods are descending; reverse for chronological charts.
  const rows = [...fin].reverse();
  const labels = rows.map((f) => String(f.period ?? "").slice(0, 4));
  const num = (f: Record<string, unknown>, k: string) =>
    f[k] != null ? Number(f[k]) : null;

  if (rows.length === 0) {
    return <p className="text-muted-foreground">本次运行未使用财务数据（可勾选 Mock 数据重跑）。</p>;
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div>
        <h4 className="text-sm font-medium mb-2">营收 / 净利润（亿元）</h4>
        <GroupedBarChart
          categories={labels}
          series={[
            { name: "营收", data: rows.map((f) => num(f, "revenue")) },
            { name: "净利润", data: rows.map((f) => num(f, "net_profit")) },
          ]}
        />
      </div>
      <div>
        <h4 className="text-sm font-medium mb-2">毛利率 / ROE（%）</h4>
        <LineChart
          categories={labels}
          series={[
            { name: "毛利率", data: rows.map((f) => num(f, "gross_margin")) },
            { name: "ROE", data: rows.map((f) => num(f, "roe")) },
          ]}
        />
      </div>
    </div>
  );
}

function MastersTab({ result }: { result: RunResult }) {
  const signals = result.master_signals ?? [];
  const NAMES = ["Warren Buffett", "Benjamin Graham", "Aswath Damodaran", "Charlie Munger", "Philip Fisher"];
  if (signals.length === 0) return <p className="text-muted-foreground">暂无大师评分</p>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {signals.map((s, i) => (
        <div key={i} className="border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium">{NAMES[i] ?? `大师 ${i + 1}`}</span>
            <SignalBadge signal={s.signal} />
          </div>
          <ConfidenceBar value={s.confidence} />
          <p className="text-sm text-muted-foreground mt-3 line-clamp-4">{s.reasoning}</p>
        </div>
      ))}
    </div>
  );
}

function DebateTab({ result }: { result: RunResult }) {
  const d = result.debate_result;
  if (!d) return <p className="text-muted-foreground">暂无辩论记录</p>;

  return (
    <div>
      <div className="bg-muted/50 border border-border rounded-lg p-4 mb-5">
        <div className="flex items-center gap-3 mb-2">
          <span className="font-medium">裁判结论</span>
          <SignalBadge signal={d.final_stance} />
          <span className="text-sm text-muted-foreground">置信度 {d.confidence.toFixed(0)}%</span>
        </div>
        <p className="text-sm">{d.judge_summary}</p>
      </div>

      <div className="space-y-4">
        {d.rounds.map((r) => (
          <div key={r.round_num}>
            <div className="text-sm font-medium mb-2">第 {r.round_num} 轮</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="border-l-4 border-emerald-400 bg-emerald-50/50 p-3 rounded-r">
                <div className="text-xs text-emerald-700 font-medium mb-1">🟢 多方</div>
                <p className="text-sm">{r.bull_argument}</p>
              </div>
              <div className="border-l-4 border-red-400 bg-red-50/50 p-3 rounded-r">
                <div className="text-xs text-red-700 font-medium mb-1">🔴 空方</div>
                <p className="text-sm">{r.bear_argument}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ValuationTab({ result }: { result: RunResult }) {
  const r = result.final_report;
  if (!r) return <p className="text-muted-foreground">暂无估值报告</p>;

  const risk = result.risk_assessment;

  const rangeOption: EChartsOption = {
    tooltip: { trigger: "axis" },
    grid: { top: 20, right: 30, bottom: 30, left: 40, containLabel: true },
    xAxis: { type: "category", data: ["低位", "中枢", "高位"] },
    yAxis: { type: "value", name: "估值" },
    series: [
      {
        type: "bar",
        data: [
          Number(r.valuation_low),
          Number(r.valuation_mid),
          Number(r.valuation_high),
        ],
        itemStyle: { color: "#4C78A8" },
        label: { show: true, position: "top" },
      },
    ],
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricTile label="低位估值" value={Number(r.valuation_low).toFixed(1)} />
        <MetricTile label="中枢估值" value={Number(r.valuation_mid).toFixed(1)} accent="primary" />
        <MetricTile label="高位估值" value={Number(r.valuation_high).toFixed(1)} />
        <MetricTile label="PE 分位" value={`${(r.pe_quantile * 100).toFixed(0)}%`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h4 className="text-sm font-medium mb-2">估值区间</h4>
          <EChart option={rangeOption} height={260} />
        </div>
        <div className="space-y-4">
          <div>
            <h4 className="text-sm font-medium text-emerald-700 mb-1">看多论据</h4>
            <ul className="text-sm space-y-1 list-disc list-inside text-muted-foreground">
              {r.bull_arguments.map((a, i) => <li key={i}>{a}</li>)}
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-medium text-red-700 mb-1">看空论据</h4>
            <ul className="text-sm space-y-1 list-disc list-inside text-muted-foreground">
              {r.bear_arguments.map((a, i) => <li key={i}>{a}</li>)}
            </ul>
          </div>
        </div>
      </div>

      {r.key_assumptions.length > 0 && (
        <div>
          <h4 className="text-sm font-medium mb-1">关键假设</h4>
          <ul className="text-sm space-y-1 list-disc list-inside text-muted-foreground">
            {r.key_assumptions.map((a, i) => <li key={i}>{a}</li>)}
          </ul>
        </div>
      )}

      {risk && (
        <div className="border border-border rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium">风险评估</span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                risk.risk_level === "high"
                  ? "bg-red-100 text-red-700"
                  : risk.risk_level === "medium"
                    ? "bg-amber-100 text-amber-700"
                    : "bg-emerald-100 text-emerald-700"
              }`}
            >
              {risk.risk_level}
            </span>
          </div>
          <p className="text-sm text-muted-foreground">{risk.falsification_result}</p>
        </div>
      )}
    </div>
  );
}
