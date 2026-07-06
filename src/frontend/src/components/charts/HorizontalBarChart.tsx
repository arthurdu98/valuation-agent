"use client";

import { EChart } from "./EChart";
import type { EChartsOption } from "echarts";

interface Props {
  categories: string[];
  values: number[];
  height?: number;
  // color positive green / negative red (for growth ranking)
  signColors?: boolean;
  suffix?: string;
}

export function HorizontalBarChart({
  categories,
  values,
  height = 300,
  signColors = false,
  suffix = "",
}: Props) {
  const option: EChartsOption = {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    grid: { top: 10, right: 60, bottom: 20, left: 80, containLabel: true },
    xAxis: { type: "value" },
    yAxis: { type: "category", data: categories },
    series: [
      {
        type: "bar",
        data: values.map((v) => ({
          value: v,
          itemStyle: {
            color: signColors ? (v >= 0 ? "#54A24B" : "#E45756") : "#4C78A8",
          },
        })),
        label: {
          show: true,
          position: "right",
          formatter: (p) => {
            const val = Number(p.value);
            return `${val > 0 && signColors ? "+" : ""}${val}${suffix}`;
          },
        },
      },
    ],
  };
  return <EChart option={option} height={height} />;
}
