"use client";

import { STAGE_ORDER, type RunState } from "@/stores/runStore";

const STAGE_LABELS: Record<string, string> = {
  l1: "L1 基础分析",
  l2: "L2 投资大师",
  l3: "L3 多空辩论",
  l4: "L4 风险证伪",
  l5: "L5 综合估值",
};

export function StageTimeline({ run }: { run: RunState }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">流水线进度</span>
        <span className="text-sm text-muted-foreground">{run.pct}%</span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden mb-5">
        <div
          className="h-full bg-primary rounded-full transition-all duration-500"
          style={{ width: `${run.pct}%` }}
        />
      </div>

      <ol className="grid grid-cols-5 gap-2">
        {STAGE_ORDER.map((key) => {
          const s = run.stages[key];
          const phase = s?.phase ?? "pending";
          return (
            <li key={key} className="text-center">
              <div
                className={`mx-auto w-9 h-9 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                  phase === "done"
                    ? "bg-emerald-500 text-white"
                    : phase === "active"
                      ? "bg-primary text-white animate-pulse"
                      : phase === "error"
                        ? "bg-red-500 text-white"
                        : "bg-muted text-muted-foreground"
                }`}
              >
                {phase === "done" ? "✓" : key.toUpperCase()}
              </div>
              <div className="text-xs mt-1.5 text-foreground">{STAGE_LABELS[key]}</div>
              {phase === "active" && s?.detail && (
                <div className="text-[11px] text-primary mt-0.5">
                  {s.detail}
                  {s.index && s.total ? ` (${s.index}/${s.total})` : ""}
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
