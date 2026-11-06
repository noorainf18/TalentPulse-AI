"use client";

import { useEffect } from "react";

type SocketHandlers = {
  onMessage?: (event: MessageEvent) => void;
  onError?: () => void;
};

export function useEvaluationSocket(candidateId: string, handlers: SocketHandlers = {}) {
  useEffect(() => {
    if (!candidateId) return;
    const base = process.env.NEXT_PUBLIC_WS_URL ?? "ws://127.0.0.1:8000";
    const ws = new WebSocket(`${base}/ws/evaluations/${candidateId}/`);

    ws.onmessage = (event) => handlers.onMessage?.(event);
    ws.onerror = () => handlers.onError?.();

    return () => {
      ws.close();
    };
  }, [candidateId, handlers]);
}
