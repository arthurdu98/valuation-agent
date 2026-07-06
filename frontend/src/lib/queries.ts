// TanStack Query hooks for server state.

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";

export function useCompaniesGrouped() {
  return useQuery({
    queryKey: ["companies", "grouped"],
    queryFn: api.companiesGrouped,
  });
}

export function useCompany(ticker: string) {
  return useQuery({
    queryKey: ["companies", ticker],
    queryFn: () => api.getCompany(ticker),
    enabled: !!ticker,
  });
}

export function useCreateCompany() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createCompany,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["companies"] }),
  });
}

export function useDeleteCompany() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteCompany,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["companies"] }),
  });
}

export function useIndustries() {
  return useQuery({ queryKey: ["industries"], queryFn: api.listIndustries });
}

export function useIndustryMetrics(industry: string | undefined) {
  return useQuery({
    queryKey: ["industry-metrics", industry],
    queryFn: () => api.industryMetrics(industry as string),
    enabled: !!industry,
  });
}

export function useCompare(industry: string) {
  return useQuery({
    queryKey: ["compare", industry],
    queryFn: () => api.compare(industry),
  });
}

export function useRunResult(runId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ["run-result", runId],
    queryFn: () => api.runResult(runId as string),
    enabled: !!runId && enabled,
  });
}
