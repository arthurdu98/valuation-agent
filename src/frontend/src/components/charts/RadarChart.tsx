"use client";

import { EChart } from "./EChart";
import type { EChartsOption } from "echarts";

interface Props {
  indicators: { name: string; max: number }[];
  series: { name: string; values: number[] }[];
  height?: number;
}

const COLORS = ["#4C78A8", "#E45756", "#54A24B", "#F58518"];

export function RadarChart({ indicators, series, height = 420 }: Props) {
  const option: EChartsOption = {
    tooltip: {},
    legend: { data: series.map((s) => s.name), bottom: 0 },
    radar: {
      indicator: indicators,
      radius: "65%",
      splitArea: { areaStyle: { color: ["#fafafa", "#f0f0f0"] } },
    },
    series: [
      {
        type: "radar",
        data: series.map((s, i) => ({
          value: s.values,
          name: s.name,
          areaStyle: { opacity: 0.15 },
          lineStyle: { color: COLORS[i % COLORS.length] },
          itemStyle: { color: COLORS[i % COLORS.length] },
        })),
      },
    ],
  };
  return <EChart option={option} height={height} />;
}
