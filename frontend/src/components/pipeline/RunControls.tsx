"use client";

import { useState } from "react";
import { useRunStream } from "@/lib/useRunStream";
import { useRunStore } from "@/stores/runStore";

export function RunControls({ ticker }: { ticker: string }) {
  const [useMock, setUseMock] = useState(true);
  const [rounds, setRounds] = useState(2);
  const { start } = useRunStream(ticker);
  const run = useRunStore((s) => s.runs[ticker]);
  const running = run?.running ?? false;

  const [starting, setStarting] = useState(false);
  const onStart = async () => {
    setStarting(true);
    try {
      await start({ useMock, debateRounds: rounds });
    } catch {
      // error surfaces via store / alert
    } finally {
      setStarting(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-5">
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={useMock}
          onChange={(e) => setUseMock(e.target.checked)}
          disabled={running}
          className="rounded"
        />
        使用内置 Mock 数据（茅台示例）
      </label>

      <label className="flex items-center gap-2 text-sm">
        辩论轮数
        <input
          type="range"
          min={1}
          max={5}
          value={rounds}
          onChange={(e) => setRounds(Number(e.target.value))}
          disabled={running}
        />
        <span className="w-4 text-center">{rounds}</span>
      </label>

      <button
        onClick={onStart}
        disabled={running || starting}
        className="ml-auto bg-primary text-primary-foreground px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50 hover:opacity-90 transition"
      >
        {running ? "分析中…" : starting ? "启动中…" : "🚀 开始分析"}
      </button>
    </div>
  );
}
