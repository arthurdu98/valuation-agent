// Hook that opens an SSE connection for a run and feeds events into the run store.

"use client";

import { useCallback, useEffect, useRef } from "react";
import { api } from "./api";
import type { ProgressEvent } from "./types";
import { useRunStore } from "@/stores/runStore";

export function useRunStream(ticker: string) {
  const esRef = useRef<EventSource | null>(null);
  const startRunState = useRunStore((s) => s.startRun);
  const applyEvent = useRunStore((s) => s.applyEvent);
  const finishRun = useRunStore((s) => s.finishRun);

  const closeStream = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
  }, []);

  const start = useCallback(
    async (opts: { useMock: boolean; debateRounds: number }) => {
      closeStream();
      const { run_id } = await api.startRun({
        ticker,
        use_mock: opts.useMock,
        debate_rounds: opts.debateRounds,
      });
      startRunState(ticker, run_id);

      const es = new EventSource(`/api/runs/${run_id}/stream`);
      esRef.current = es;

      const onProgress = (e: MessageEvent) => {
        try {
          const ev: ProgressEvent = JSON.parse(e.data);
          applyEvent(ticker, ev);
        } catch {
          // ignore malformed frames
        }
      };

      es.addEventListener("progress", onProgress);
      es.addEventListener("error", (e) => {
        const me = e as MessageEvent;
        if (me.data) {
          try {
            applyEvent(ticker, JSON.parse(me.data));
          } catch {
            /* noop */
          }
        }
      });
      es.addEventListener("done", (e) => {
        const me = e as MessageEvent;
        let err: string | null = null;
        try {
          const data = JSON.parse(me.data);
          if (data.status === "error") err = "运行出错";
        } catch {
          /* noop */
        }
        finishRun(ticker, err);
        closeStream();
      });
      // Native EventSource error (network / stream closed by server after done).
      es.onerror = () => {
        // If the server already sent "done" we've closed; otherwise mark finished.
        if (esRef.current) {
          finishRun(ticker, null);
          closeStream();
        }
      };

      return run_id;
    },
    [ticker, applyEvent, finishRun, startRunState, closeStream],
  );

  useEffect(() => closeStream, [closeStream]);

  return { start, closeStream };
}
