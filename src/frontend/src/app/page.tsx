"use client";

import Link from "next/link";
import { useCompaniesGrouped } from "@/lib/queries";
import { Card, CardBody } from "@/components/common/Card";

export default function HomePage() {
  const { data, isLoading, error } = useCompaniesGrouped();

  if (isLoading) return <PageSkeleton />;
  if (error) return <p className="text-destructive">加载失败：{(error as Error).message}</p>;
  if (!data) return null;

  const industries = Object.entries(data);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">追踪公司概览</h1>

      {industries.map(([industry, companies]) => (
        <section key={industry} className="mb-8">
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">🏭 {industry}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {companies.map((c) => (
              <Link key={c.ticker} href={`/companies/${c.ticker}`}>
                <Card className="hover:border-primary transition-colors cursor-pointer h-full">
                  <CardBody>
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-medium text-foreground">{c.name}</div>
                        <div className="text-sm text-muted-foreground mt-1">{c.ticker}</div>
                      </div>
                      <span className="text-xs bg-muted px-2 py-0.5 rounded">
                        {c.market.toUpperCase()}
                      </span>
                    </div>
                    {c.competitors.length > 0 && (
                      <div className="text-xs text-muted-foreground mt-3">
                        竞对：{c.competitors.slice(0, 3).join(", ")}
                      </div>
                    )}
                  </CardBody>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function PageSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-8 w-48 bg-muted rounded" />
      {[1, 2, 3].map((i) => (
        <div key={i} className="space-y-3">
          <div className="h-5 w-24 bg-muted rounded" />
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3].map((j) => (
              <div key={j} className="h-24 bg-muted rounded-lg" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
