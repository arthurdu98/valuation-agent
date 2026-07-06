"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";

// Lightweight ECharts wrapper — avoids echarts-for-react to keep control over
// resize + dispose. Renders nothing on the server.
export function EChart({
  option,
  height = 320,
  className = "",
}: {
  option: EChartsOption;
  height?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chartRef.current = chart;

    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, true);
  }, [option]);

  return <div ref={ref} style={{ height }} className={className} />;
}

// Shared palette matching the old Plotly colors.
export const PALETTE = {
  blue: "#4C78A8",
  teal: "#72B7B2",
  orange: "#F58518",
  green: "#54A24B",
  yellow: "#EECA3B",
  purple: "#B279A2",
  red: "#E45756",
};
