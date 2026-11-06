/**
 * API client: prefer same-origin `/api/*` (Next rewrites → Django) so session cookies work.
 * Server-side fetch uses NEXT_PUBLIC_API_URL / INTERNAL_API_URL.
 *
 * CSRF: Django session + unsafe methods require X-CSRFToken (see Django CSRF docs).
 * https://docs.djangoproject.com/en/stable/ref/csrf/
 */

import type {
  AgentRunResponse,
  AgentStatus,
  CandidatesListResponse,
  DashboardSummaryResponse,
  EvidencePanel,
  FeedbackRequest,
  FeedbackResponse,
  RagAskRequest,
  RagAskResponse,
  UploadResponse,
  VoiceInterviewDetail,
  VoiceInterviewSummary,
  VoiceSessionBrief,
} from "@/lib/types";

export type AuthUser = {
  id: number;
  email: string;
  name: string;
  is_staff: boolean;
  is_superuser: boolean;
};

export function getApiBase(): string {
  if (typeof window !== "undefined") {
    return "";
  }
  return (
    process.env.INTERNAL_API_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://127.0.0.1:8000"
  );
}

/** Step 1 for session auth: cookie + token for unsafe requests (call on app load or before POST). */
export async function getCsrfToken(): Promise<string> {
  const url = `${getApiBase()}/api/auth/csrf/`;
  let res: Response;
  try {
    res = await fetch(url, {
      credentials: "include",
      cache: "no-store",
    });
  } catch {
    throw new Error(
      "Cannot reach Django at 127.0.0.1:8000. In a second terminal run: python manage.py runserver 127.0.0.1:8000 — then refresh this page.",
    );
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const j = (await res.json()) as { detail?: string };
      if (j.detail) detail = j.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  const data = (await res.json()) as { csrfToken: string };
  return data.csrfToken;
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const needsCsrf = ["POST", "PUT", "PATCH", "DELETE"].includes(method);
  const headers: Record<string, string> = {
    ...((options.headers as Record<string, string>) ?? {}),
  };
  if (needsCsrf && !headers["X-CSRFToken"]) {
    headers["X-CSRFToken"] = await getCsrfToken();
  }
  if (
    method !== "GET" &&
    method !== "HEAD" &&
    !headers["Content-Type"] &&
    typeof options.body === "string"
  ) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${getApiBase()}${path}`, {
    credentials: "include",
    ...options,
    headers,
  });

  if (!res.ok) {
    let message = `API error ${res.status}`;
    const text = await res.text(); // read ONCE
    try {
      const body = JSON.parse(text);
      if (body.detail) message = body.detail;
      else if (body.error) message = body.error;
      else if (body.resume) message = body.resume[0];
      else message = JSON.stringify(body);
    } catch {
      message = text; // was already plain text
    }
    throw new Error(message);
  }

  if (res.status === 204) return {} as T;
  return res.json() as Promise<T>;
}

export async function fetchAuthMe(): Promise<AuthUser> {
  return apiFetch<AuthUser>("/api/auth/me/");
}

export async function loginWithSession(email: string, password: string): Promise<{ user: AuthUser }> {
  const normalizedEmail = email.trim().toLowerCase();
  return apiFetch<{ user: AuthUser }>("/api/auth/login/", {
    method: "POST",
    body: JSON.stringify({ email: normalizedEmail, password }),
  });
}

export async function logoutSession(): Promise<void> {
  await apiFetch("/api/auth/logout/", { method: "POST" });
}

export async function uploadResume(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("resume", file);
  const csrf = await getCsrfToken();

  const res = await fetch(`${getApiBase()}/api/candidates/upload/`, {
    method: "POST",
    credentials: "include",
    headers: { "X-CSRFToken": csrf },
    body: form,
  });

  if (!res.ok) {
    let message = `Upload failed (${res.status})`;
    try {
      const body = await res.json();
      if (body.error) message = body.error;
      if (body.resume) message = body.resume[0];
    } catch {
      message = await res.text();
    }
    throw new Error(message);
  }

  const body = await res.json();
  if (res.status === 200) {
    return { kind: "duplicate", message: body.message, candidate_id: body.candidate_id };
  }
  return { kind: "created", message: body.message, candidate_id: body.candidate_id };
}

export function fetchCandidates(params?: {
  status?: string;
  min_score?: number;
}): Promise<CandidatesListResponse> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.min_score) qs.set("min_score", String(params.min_score));
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch(`/api/dashboard/candidates/${query}`);
}

export function fetchDashboardSummary(): Promise<DashboardSummaryResponse> {
  return apiFetch("/api/dashboard/summary/");
}

export async function fetchEvidencePanel(candidateId: string): Promise<EvidencePanel> {
  const res = await fetch(`${getApiBase()}/api/dashboard/candidate/${candidateId}/`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });

  if (res.status === 404) throw new Error("Candidate not found.");
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }

  const body = await res.json();
  if (res.status === 202) {
    return {
      kind: "pending",
      candidate_id: body.candidate_id ?? candidateId,
      candidate_name: body.candidate_name ?? "",
      status: "pending",
      message: body.message ?? "Evaluation in progress.",
    };
  }
  return { kind: "ready", ...body };
}

export function fetchAgentStatus(candidateId: string): Promise<AgentStatus> {
  return apiFetch(`/api/agent/status/${candidateId}/`);
}

export function triggerRescreening(candidateId: string): Promise<AgentRunResponse> {
  return apiFetch("/api/agent/run/", {
    method: "POST",
    body: JSON.stringify({ candidate_id: candidateId }),
  });
}

export function submitFeedback(payload: FeedbackRequest): Promise<FeedbackResponse> {
  return apiFetch("/api/dashboard/feedback/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * FIX: askRagChat now serialises the full RagAskRequest payload including
 * candidate_id. Previously, even though RagAskRequest typed candidate_id as
 * optional, JSON.stringify on the payload object will include it when present
 * — so this function itself was fine structurally. The real gaps were:
 *   1. The serializer didn't declare candidate_id (fixed in serializers.py).
 *   2. The chatbot page never passed candidate_id into this call (fixed in
 *      page.tsx via the candidateId prop / URL search param).
 * This function is unchanged in logic but the comment documents the contract.
 */
export function askRagChat(payload: RagAskRequest): Promise<RagAskResponse> {
  return apiFetch("/api/ragchat/ask/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ── Voice screening ─────────────────────────────────────────────────────────

export type InitiateVoiceScreenResponse = {
  message: string;
  interview_id?: string;
  status?: string;
};

export async function initiateVoiceScreen(
  evaluationId: string,
  scheduledAt?: string | null,
): Promise<InitiateVoiceScreenResponse> {
  const body: { evaluation_id: string; scheduled_at?: string } = {
    evaluation_id: evaluationId,
  };
  if (scheduledAt) body.scheduled_at = scheduledAt;
  return apiFetch("/api/voice/initiate/", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchVoiceInterviewDetail(interviewId: string): Promise<VoiceInterviewDetail> {
  return apiFetch(`/api/voice/${interviewId}/`);
}

export function fetchVoiceInterviewStatus(interviewId: string): Promise<VoiceInterviewSummary> {
  return apiFetch(`/api/voice/${interviewId}/status/`);
}

export async function skipVoiceInterview(interviewId: string): Promise<{ message: string }> {
  return apiFetch(`/api/voice/${interviewId}/skip/`, { method: "POST" });
}

export type VoiceJoinResponse = {
  /** Added by API; older servers may omit — use NEXT_PUBLIC_LIVEKIT_URL fallback in UI. */
  livekit_server_url?: string;
  livekit_token: string;
  room_name: string;
  candidate_name: string;
  interview_id: string;
};

/** Candidate join — no Django session; token is the interview session_token UUID. */
export async function fetchVoiceJoin(token: string): Promise<VoiceJoinResponse> {
  const res = await fetch(
    `${getApiBase()}/api/voice/join/?token=${encodeURIComponent(token)}`,
    { credentials: "omit", cache: "no-store" },
  );
  if (!res.ok) {
    const text = await res.text();
    let message = `API error ${res.status}`;
    try {
      const body = JSON.parse(text) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      message = text || message;
    }
    throw new Error(message);
  }
  return res.json() as Promise<VoiceJoinResponse>;
}

/** Candidate session brief — same token auth as join; no Django session cookie. */
export async function fetchVoiceSessionBrief(token: string): Promise<VoiceSessionBrief> {
  const res = await fetch(
    `${getApiBase()}/api/voice/session/?token=${encodeURIComponent(token)}`,
    { credentials: "omit", cache: "no-store" },
  );
  if (!res.ok) {
    const text = await res.text();
    let message = `API error ${res.status}`;
    try {
      const body = JSON.parse(text) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      message = text || message;
    }
    throw new Error(message);
  }
  return res.json() as Promise<VoiceSessionBrief>;
}