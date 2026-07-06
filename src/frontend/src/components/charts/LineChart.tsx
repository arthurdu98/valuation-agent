"use client";

import { EChart, PALETTE } from "./EChart";
import type { EChartsOption } from "echarts";

interface Props {
  categories: string[];
  series: { name: string; data: (number | null)[]; color?: string }[];
  height?: number;
}

export function LineChart({ categories, series, height = 300 }: Props) {
  const colors = [PALETTE.red, PALETTE.green, PALETTE.blue, PALETTE.orange];
  const option: EChartsOption = {
    tooltip: { trigger: "axis" },
    legend: { data: series.map((s) => s.name), bottom: 0 },
    grid: { top: 20, right: 20, bottom: 40, left: 50, containLabel: true },
    xAxis: { type: "category", data: categories, boundaryGap: false },
    yAxis: { type: "value" },
    series: series.map((s, i) => ({
      name: s.name,
      type: "line" as const,
      data: s.data,
      smooth: true,
      symbol: "circle",
      symbolSize: 6,
      lineStyle: { color: s.color ?? colors[i % colors.length] },
      itemStyle: { color: s.color ?? colors[i % colors.length] },
    })),
  };
  return <EChart option={option} height={height} />;
}
