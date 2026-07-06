"use client";

import { useState } from "react";
import { useCompaniesGrouped, useIndustryMetrics } from "@/lib/queries";
import { api } from "@/lib/api";
import { Card, CardBody, CardHeader } from "@/components/common/Card";
import type { Company, MetricDefinition } from "@/lib/types";

const MODE_ICON: Record<string, string> = {
  auto: "🤖",
  semi_auto: "⚙️",
  manual: "✍️",
};

export default function MetricsPage() {
  const { data: grouped } = useCompaniesGrouped();
  const allCompanies = grouped ? Object.values(grouped).flat() : [];
  const [selectedTicker, setSelectedTicker] = useState("");
  const selectedCompany: Company | undefined = allCompanies.find(
    (c) => c.ticker === selectedTicker,
  );
  const { data: metrics } = useIndustryMetrics(selectedCompany?.industry);

  const [values, setValues] = useState<Record<string, number>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ saved: number } | null>(null);

  const handleSubmit = async () => {
    if (!selectedCompany || !metrics) return;
    setSubmitting(true);
    setResult(null);
    try {
      const res = await api.submitMetrics({
        ticker: selectedCompany.ticker,
        industry: selectedCompany.industry,
        values,
      });
      setResult(res);
    } catch (e) {
      alert(`提交失败: ${(e as Error).message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">行业指标录入</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <label className="text-sm font-medium mb-1 block">选择公司</label>
          <select
            value={selectedTicker}
            onChange={(e) => {
              setSelectedTicker(e.target.value);
              setValues({});
              setResult(null);
            }}
            className="w-full border border-border rounded-md px-3 py-2 text-sm bg-card"
          >
            <option value="">-- 请选择 --</option>
            {allCompanies.map((c) => (
              <option key={c.ticker} value={c.ticker}>
                {c.name} ({c.ticker})
              </option>
            ))}
          </select>
        </div>
        {selectedCompany && (
          <div className="flex items-end">
            <span className="text-sm bg-muted px-3 py-2 rounded-md">
              行业：{selectedCompany.industry}
            </span>
          </div>
        )}
      </div>

      {metrics && metrics.length > 0 && (
        <Card>
          <CardHeader
            title="指标录入"
            subtitle={`${selectedCompany?.industry} · ${metrics.length} 个指标`}
          />
          <CardBody>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {metrics.map((m: MetricDefinition) => (
                <div key={m.name}>
                  <label className="flex items-center gap-2 text-sm font-medium mb-1">
                    <span title={m.collection_mode}>
                      {MODE_ICON[m.collection_mode] ?? "📝"}
                    </span>
                    {m.display_name}
                  </label>
                  <input
                    type="number"
                    step="any"
                    placeholder={m.description}
                    value={values[m.name] ?? ""}
                    onChange={(e) =>
                      setValues((v) => ({
                        ...v,
                        [m.name]: e.target.value ? Number(e.target.value) : 0,
                      }))
                    }
                    className="w-full border border-border rounded-md px-3 py-2 text-sm bg-card"
                  />
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {m.description}
                  </p>
                </div>
              ))}
            </div>

            <div className="mt-6 flex items-center gap-4">
              <button
                onClick={handleSubmit}
                disabled={submitting || Object.keys(values).length === 0}
                className="bg-primary text-primary-foreground px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50 hover:opacity-90 transition"
              >
                {submitting ? "提交中…" : "提交指标"}
              </button>
              {result && (
                <span className="text-sm text-success">
                  ✓ 已保存 {result.saved} 条记录
                </span>
              )}
            </div>
          </CardBody>
        </Card>
      )}

      {selectedCompany && metrics && metrics.length === 0 && (
        <p className="text-muted-foreground">该行业暂无定义指标。</p>
      )}

      {/* Screenshot upload stub */}
      {selectedCompany && (
        <Card className="mt-6">
          <CardHeader title="📸 截图识别" subtitle="上传年报/研报截图，LLM 视觉识别自动提取" />
          <CardBody>
            <div className="border-2 border-dashed border-border rounded-lg p-8 text-center text-muted-foreground">
              <p>拖拽截图到此处或点击上传</p>
              <p className="text-xs mt-2">（LLM 视觉识别功能将在接入后自动提取数据）</p>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
