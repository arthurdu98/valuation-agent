// Typed fetch client. All requests go through the Next.js rewrite (/api/* -> backend).

import type {
  Company,
  ComparisonRow,
  MetricDefinition,
  MetricSubmitResult,
  RunCreated,
  RunResult,
  RunStatus,
  RunSummary,
} from "./types";

const BASE = ""; // same-origin; next.config rewrites /api to the backend

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore non-JSON errors
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // Companies
  listCompanies: (params?: { industry?: string; market?: string }) => {
    const q = new URLSearchParams();
    if (params?.industry) q.set("industry", params.industry);
    if (params?.market) q.set("market", params.market);
    const qs = q.toString();
    return request<Company[]>(`/api/companies${qs ? `?${qs}` : ""}`);
  },
  companiesGrouped: () => request<Record<string, Company[]>>("/api/companies/grouped"),
  getCompany: (ticker: string) => request<Company>(`/api/companies/${ticker}`),
  createCompany: (payload: {
    ticker: string;
    name: string;
    market: string;
    industry: string;
    competitors: string[];
  }) => request<Company>("/api/companies", { method: "POST", body: JSON.stringify(payload) }),
  deleteCompany: (ticker: string) =>
    request<{ success: boolean }>(`/api/companies/${ticker}`, { method: "DELETE" }),

  // Industries
  listIndustries: () => request<string[]>("/api/industries"),
  industryMetrics: (industry: string) =>
    request<MetricDefinition[]>(`/api/industries/${encodeURIComponent(industry)}/metrics`),

  // Compare
  compare: (industry = "全部") =>
    request<{ rows: ComparisonRow[] }>(`/api/compare?industry=${encodeURIComponent(industry)}`),

  // Runs
  startRun: (payload: { ticker: string; use_mock: boolean; debate_rounds: number }) =>
    request<RunCreated>("/api/runs", { method: "POST", body: JSON.stringify(payload) }),
  listRuns: () => request<RunSummary[]>("/api/runs"),
  runStatus: (runId: string) => request<RunStatus>(`/api/runs/${runId}`),
  runResult: (runId: string) => request<RunResult>(`/api/runs/${runId}/result`),

  // Metrics
  submitMetrics: (payload: {
    ticker: string;
    industry: string;
    record_date?: string;
    values: Record<string, number>;
  }) => request<MetricSubmitResult>("/api/metrics", { method: "POST", body: JSON.stringify(payload) }),

  // Report URLs (used directly as download links)
  reportMarkdownUrl: (runId: string) => `/api/reports/${runId}/markdown`,
  reportPdfUrl: (runId: string) => `/api/reports/${runId}/pdf`,
};
