"use client";

import { useEffect, useRef } from "react";

type VoiceWsPayload = Record<string, unknown>;

/**
 * Recruiter dashboard: live events for one voice session (session_token UUID).
 * Backend: ws/voice/<session_token>/
 */
export function useVoiceSessionSocket(
  sessionToken: string | null,
  onEvent: (payload: VoiceWsPayload) => void,
) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!sessionToken) return;
    const base = process.env.NEXT_PUBLIC_WS_URL ?? "ws://127.0.0.1:8000";
    const ws = new WebSocket(`${base}/ws/voice/${sessionToken}/`);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string) as VoiceWsPayload;
        onEventRef.current(data);
      } catch {
        /* ignore */
      }
    };

    const ping = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: "ping" }));
      }
    }, 25_000);

    return () => {
      clearInterval(ping);
      ws.close();
    };
  }, [sessionToken]);
}
