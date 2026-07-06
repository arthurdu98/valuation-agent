// Zustand store for live pipeline-run state, keyed by ticker.
// The SSE hook writes progress here; components subscribe for real-time updates.

import { create } from "zustand";
import type { ProgressEvent, StageKey } from "@/lib/types";

export type StagePhase = "pending" | "active" | "done" | "error";

export interface StageState {
  phase: StagePhase;
  detail?: string; // e.g. "Charlie Munger" or "第 2 轮"
  index?: number;
  total?: number;
}

const STAGE_ORDER: StageKey[] = ["l1", "l2", "l3", "l4", "l5"];

export interface RunState {
  runId: string | null;
  ticker: string | null;
  running: boolean;
  finished: boolean;
  error: string | null;
  pct: number;
  stages: Record<string, StageState>;
  events: ProgressEvent[];
}

function initialStages(): Record<string, StageState> {
  return Object.fromEntries(STAGE_ORDER.map((s) => [s, { phase: "pending" as StagePhase }]));
}

interface RunStore {
  runs: Record<string, RunState>; // keyed by ticker
  startRun: (ticker: string, runId: string) => void;
  applyEvent: (ticker: string, ev: ProgressEvent) => void;
  finishRun: (ticker: string, error?: string | null) => void;
  reset: (ticker: string) => void;
  get: (ticker: string) => RunState | undefined;
}

export const useRunStore = create<RunStore>((set, get) => ({
  runs: {},

  startRun: (ticker, runId) =>
    set((state) => ({
      runs: {
        ...state.runs,
        [ticker]: {
          runId,
          ticker,
          running: true,
          finished: false,
          error: null,
          pct: 0,
          stages: initialStages(),
          events: [],
        },
      },
    })),

  applyEvent: (ticker, ev) =>
    set((state) => {
      const run = state.runs[ticker];
      if (!run) return state;

      const stages = { ...run.stages };
      let pct = run.pct;
      let error = run.error;

      if (ev.stage === "error") {
        error = ev.message ?? "运行出错";
      } else if (ev.stage !== "done" && stages[ev.stage]) {
        const cur = { ...stages[ev.stage] };
        if (ev.status === "start") {
          cur.phase = "active";
        } else if (ev.status === "done") {
          cur.phase = "done";
        } else if (ev.status === "progress") {
          cur.phase = "active";
          cur.detail = ev.detail;
          cur.index = ev.index ?? ev.round;
          cur.total = ev.total;
        }
        stages[ev.stage] = cur;
      }

      if (typeof ev.pct === "number") pct = ev.pct;

      return {
        runs: {
          ...state.runs,
          [ticker]: { ...run, stages, pct, error, events: [...run.events, ev] },
        },
      };
    }),

  finishRun: (ticker, error) =>
    set((state) => {
      const run = state.runs[ticker];
      if (!run) return state;
      return {
        runs: {
          ...state.runs,
          [ticker]: {
            ...run,
            running: false,
            finished: true,
            error: error ?? run.error,
            pct: error ? run.pct : 100,
          },
        },
      };
    }),

  reset: (ticker) =>
    set((state) => {
      const next = { ...state.runs };
      delete next[ticker];
      return { runs: next };
    }),

  get: (ticker) => get().runs[ticker],
}));

export { STAGE_ORDER };
