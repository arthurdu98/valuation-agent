export function MetricTile({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "primary" | "success" | "danger" | "neutral";
}) {
  const valueColor =
    accent === "success"
      ? "text-emerald-600"
      : accent === "danger"
        ? "text-red-600"
        : accent === "primary"
          ? "text-primary"
          : "text-foreground";
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className={`text-2xl font-semibold mt-1 ${valueColor}`}>{value}</div>
      {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
    </div>
  );
}
