"use client";

import { EChart, PALETTE } from "./EChart";
import type { EChartsOption } from "echarts";

interface Props {
  categories: string[];
  series: { name: string; data: (number | null)[]; color?: string }[];
  height?: number;
}

export function GroupedBarChart({ categories, series, height = 340 }: Props) {
  const colors = [PALETTE.blue, PALETTE.teal, PALETTE.orange, PALETTE.green, PALETTE.yellow, PALETTE.purple];
  const option: EChartsOption = {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { data: series.map((s) => s.name), bottom: 0 },
    grid: { top: 20, right: 20, bottom: 40, left: 50, containLabel: true },
    xAxis: { type: "category", data: categories },
    yAxis: { type: "value" },
    series: series.map((s, i) => ({
      name: s.name,
      type: "bar" as const,
      data: s.data,
      itemStyle: { color: s.color ?? colors[i % colors.length] },
    })),
  };
  return <EChart option={option} height={height} />;
}
