"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "首页", icon: "🏠" },
  { href: "/compare", label: "行业对比", icon: "📊" },
  { href: "/metrics", label: "指标录入", icon: "✍️" },
  { href: "/reports", label: "报告导出", icon: "📋" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 shrink-0 border-r border-border bg-card flex flex-col">
      <div className="p-5 border-b border-border">
        <div className="text-lg font-semibold text-foreground">📈 估值监控</div>
        <div className="text-xs text-muted-foreground mt-1">多智能体辩证分析</div>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {NAV.map((item) => {
          const active =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                active
                  ? "bg-primary text-primary-foreground font-medium"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="p-4 text-xs text-muted-foreground border-t border-border">
        L1-L5 流水线 · A股/港股/美股
      </div>
    </aside>
  );
}
