// TS mirror of the API contracts (src/schemas.py + src/api/schemas_api.py).

export type Market = "a_share" | "hk" | "us";
export type Signal = "bullish" | "bearish" | "neutral";
export type CollectionMode = "auto" | "semi_auto" | "manual";

export interface Company {
  id: string | null;
  ticker: string;
  name: string;
  market: Market;
  industry: string;
  competitors: string[];
  custom_groups: string[];
  is_active: boolean;
  created_at: string | null;
}

export interface MetricDefinition {
  name: string;
  display_name: string;
  data_type: string;
  collection_mode: CollectionMode;
  alert_threshold: number | null;
  description: string;
}

export interface AlertRule {
  name: string;
  condition: string;
  threshold: number;
  severity: string;
  description: string;
}

export interface ComparisonRow {
  ticker: string;
  name: string;
  industry: string;
  market: string;
  pe: number | null;
  pb: number | null;
  ps: number | null;
  gross_margin: number | null;
  roe: number | null;
  revenue_growth: number | null;
  net_margin: number | null;
  market_cap_bn: number | null;
}

export interface MasterSignal {
  signal: Signal;
  confidence: number;
  reasoning: string;
}

export interface DebateRound {
  round_num: number;
  bull_argument: string;
  bear_argument: string;
}

export interface DebateResult {
  rounds: DebateRound[];
  judge_summary: string;
  final_stance: Signal;
  confidence: number;
  key_contentions: string[];
}

export interface ValuationReport {
  ticker: string;
  valuation_low: string;
  valuation_mid: string;
  valuation_high: string;
  pe_quantile: number;
  bull_arguments: string[];
  bear_arguments: string[];
  key_assumptions: string[];
  sensitivity_factors: Record<string, unknown>;
  competitor_comparison: Record<string, unknown>;
  human_approved: boolean;
}

export interface RiskAssessment {
  risk_level: string;
  risks: string[];
  falsification_result: string;
  confidence_adjustment: number;
}

// The full ValuationState returned by GET /api/runs/{id}/result.
export interface RunResult {
  ticker?: string;
  company?: { name: string };
  financial_data?: Record<string, unknown>[];
  master_signals?: MasterSignal[];
  debate_result?: DebateResult;
  risk_assessment?: RiskAssessment;
  final_report?: ValuationReport;
  dcf_value?: number | null;
  monte_carlo_percentiles?: Record<string, number> | null;
  error?: string | null;
}

// --- Run lifecycle ---

export interface RunCreated {
  run_id: string;
  status: string;
}

export interface RunSummary {
  run_id: string;
  ticker: string;
  company_name: string;
  status: string;
  created_at: string;
}

export interface RunStatus extends RunSummary {
  error: string | null;
  result_available: boolean;
}

// --- SSE progress events ---

export type StageKey = "l1" | "l2" | "l3" | "l4" | "l5" | "done" | "error";

export interface ProgressEvent {
  stage: StageKey;
  status: "start" | "done" | "progress" | "error";
  label?: string;
  detail?: string;
  index?: number;
  total?: number;
  round?: number;
  pct?: number;
  message?: string;
  result_available?: boolean;
}

export interface MetricSubmitResult {
  saved: number;
  records: Record<string, unknown>[];
}
