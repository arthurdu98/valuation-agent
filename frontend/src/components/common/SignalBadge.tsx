import type { Signal } from "@/lib/types";

const CONFIG: Record<Signal, { label: string; cls: string; dot: string }> = {
  bullish: { label: "看多", cls: "bg-emerald-50 text-emerald-700 border-emerald-200", dot: "🟢" },
  bearish: { label: "看空", cls: "bg-red-50 text-red-700 border-red-200", dot: "🔴" },
  neutral: { label: "中性", cls: "bg-amber-50 text-amber-700 border-amber-200", dot: "🟡" },
};

export function SignalBadge({ signal }: { signal: Signal }) {
  const c = CONFIG[signal] ?? CONFIG.neutral;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${c.cls}`}
    >
      <span>{c.dot}</span>
      {c.label}
    </span>
  );
}
