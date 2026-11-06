"use client";

import { Copy, Mic, Radio, SkipForward } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchVoiceInterviewDetail,
  fetchVoiceInterviewStatus,
  initiateVoiceScreen,
  skipVoiceInterview,
} from "@/lib/api";
import type { VoiceInterviewDetail } from "@/lib/types";
import { aosFadeStagger } from "@/lib/aos";

import { useVoiceSessionSocket } from "./useVoiceSessionSocket";

const ACTIVE_LIKE = new Set(["pending", "invited", "active"]);

function statusLabel(status: string) {
  return status.replace(/_/g, " ");
}

type Props = {
  candidateId: string;
  evaluationId: string;
  initialInterview: VoiceInterviewDetail | null;
  sectionClassName?: string;
};

export default function VoiceScreenPanel({
  candidateId,
  evaluationId,
  initialInterview,
  sectionClassName = "",
}: Props) {
  const qc = useQueryClient();
  const [liveHint, setLiveHint] = useState<string | null>(null);

  const detailQuery = useQuery({
    queryKey: ["voiceInterview", initialInterview?.id],
    queryFn: () => fetchVoiceInterviewDetail(initialInterview!.id),
    enabled: Boolean(initialInterview?.id),
    initialData: initialInterview ?? undefined,
  });

  const interview = detailQuery.data ?? initialInterview;

  const statusQuery = useQuery({
    queryKey: ["voiceInterviewStatus", interview?.id],
    queryFn: () => fetchVoiceInterviewStatus(interview!.id),
    enabled: Boolean(interview?.id) && interview?.status === "active",
    refetchInterval: interview?.status === "active" ? 4000 : false,
  });

  const mergedStatus = statusQuery.data?.status ?? interview?.status ?? "";

  useVoiceSessionSocket(
    interview?.status === "active" ? interview.session_token : null,
    useCallback((payload) => {
      const ev = typeof payload.event === "string" ? payload.event : "";
      if (ev) setLiveHint(ev);
    }, []),
  );

  const initiate = useMutation({
    mutationFn: () => initiateVoiceScreen(evaluationId),
    onSuccess: () => {
      toast.success("Voice screen scheduled.");
      void qc.invalidateQueries({ queryKey: ["evaluation", candidateId] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const skip = useMutation({
    mutationFn: () => skipVoiceInterview(interview!.id),
    onSuccess: () => {
      toast.success("Voice screen skipped.");
      void qc.invalidateQueries({ queryKey: ["evaluation", candidateId] });
      void detailQuery.refetch();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const copyJoin = useCallback(() => {
    if (!interview?.join_url) return;
    void navigator.clipboard.writeText(interview.join_url);
    toast.success("Invite link copied.");
  }, [interview?.join_url]);

  const canSkip = useMemo(() => {
    if (!interview) return false;
    return interview.status === "pending" || interview.status === "invited";
  }, [interview]);

  if (!interview) {
    return (
      <section
        className={`rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-6 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md ${sectionClassName}`}
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#9fffe6]">Voice screen</p>
            <h2 className="mt-2 text-xl font-semibold text-white">Structured voice interview</h2>
            <p className="mt-2 text-base text-slate-300">
              Schedule a LiveKit voice session for this candidate. They receive a link to join from their browser.
            </p>
          </div>
          <button
            type="button"
            onClick={() => initiate.mutate()}
            disabled={initiate.isPending}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl border border-[rgba(0,230,195,0.45)] bg-[rgba(0,230,200,0.12)] px-5 py-2.5 text-sm font-semibold text-[#9fffe6] transition hover:bg-[rgba(0,230,200,0.2)] disabled:opacity-50"
          >
            <Mic className="h-4 w-4" />
            {initiate.isPending ? "Scheduling…" : "Schedule voice screen"}
          </button>
        </div>
      </section>
    );
  }

  return (
    <div className={`space-y-6 ${sectionClassName}`}>
      <section
        className={`rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-6 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md ${aosFadeStagger(0)}`}
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#9fffe6]">Voice screen</p>
            <h2 className="mt-2 text-xl font-semibold text-white">Session status</h2>
            <p className="mt-2 text-base capitalize text-slate-300">{statusLabel(mergedStatus)}</p>
            {mergedStatus === "active" && (
              <p className="mt-2 flex items-center gap-2 text-sm text-[#9fffe6]">
                <Radio className="h-4 w-4 animate-pulse" />
                Live — updates stream while the candidate is in the room.
              </p>
            )}
            {liveHint && mergedStatus === "active" && (
              <p className="mt-1 font-mono text-xs text-slate-400">{liveHint}</p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {ACTIVE_LIKE.has(interview.status) && interview.join_url && (
              <button
                type="button"
                onClick={copyJoin}
                className="inline-flex items-center gap-2 rounded-xl border border-[rgba(0,230,195,0.35)] bg-[rgba(15,42,51,0.6)] px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-[rgba(0,230,195,0.55)] hover:text-white"
              >
                <Copy className="h-4 w-4" />
                Copy invite link
              </button>
            )}
            {canSkip && (
              <button
                type="button"
                onClick={() => skip.mutate()}
                disabled={skip.isPending}
                className="inline-flex items-center gap-2 rounded-xl border border-rose-300/30 bg-rose-900/25 px-4 py-2 text-sm font-medium text-rose-100 transition hover:bg-rose-900/40 disabled:opacity-50"
              >
                <SkipForward className="h-4 w-4" />
                Skip voice screen
              </button>
            )}
          </div>
        </div>

        {(interview.voice_composite_score != null || interview.final_merged_score != null) && (
          <dl className="mt-6 grid gap-4 sm:grid-cols-2">
            {interview.voice_composite_score != null && (
              <div className="rounded-xl border border-[rgba(0,230,200,0.1)] bg-[rgba(6,20,32,0.5)] p-4">
                <dt className="text-xs uppercase tracking-wider text-slate-400">Voice composite</dt>
                <dd className="mt-1 text-2xl font-bold text-white">{interview.voice_composite_score.toFixed(1)}</dd>
              </div>
            )}
            {interview.final_merged_score != null && (
              <div className="rounded-xl border border-[rgba(0,230,200,0.1)] bg-[rgba(6,20,32,0.5)] p-4">
                <dt className="text-xs uppercase tracking-wider text-slate-400">Merged score</dt>
                <dd className="mt-1 text-2xl font-bold text-[#9fffe6]">{interview.final_merged_score.toFixed(1)}</dd>
              </div>
            )}
          </dl>
        )}

        {interview.error_message && (
          <p className="mt-4 rounded-lg border border-rose-300/25 bg-rose-950/40 p-3 text-sm text-rose-100">
            {interview.error_message}
          </p>
        )}
      </section>

      {interview.transcript_text && (
        <section
          className={`rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-6 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md ${aosFadeStagger(1)}`}
        >
          <h3 className="text-lg font-semibold text-white">Transcript</h3>
          <pre className="mt-3 max-h-[320px] overflow-auto whitespace-pre-wrap text-sm leading-relaxed text-slate-300">
            {interview.transcript_text}
          </pre>
        </section>
      )}

      {interview.questions.length > 0 && (
        <section
          className={`rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-6 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md ${aosFadeStagger(2)}`}
        >
          <h3 className="text-lg font-semibold text-white">Questions & answers</h3>
          <ul className="mt-4 space-y-4">
            {interview.questions
              .slice()
              .sort((a, b) => a.sequence_order - b.sequence_order)
              .map((q) => (
                <li
                  key={q.id}
                  className="rounded-xl border border-[rgba(0,230,200,0.08)] bg-[rgba(6,20,32,0.45)] p-4"
                >
                  <p className="text-sm font-semibold text-[#9fffe6]">
                    Q{q.sequence_order}
                    {q.target_skill ? ` · ${q.target_skill}` : ""}
                  </p>
                  <p className="mt-2 text-base text-slate-200">{q.question_text}</p>
                  {q.answer?.answer_text && (
                    <p className="mt-3 border-t border-white/10 pt-3 text-sm text-slate-300">{q.answer.answer_text}</p>
                  )}
                  {q.answer?.answer_score != null && (
                    <p className="mt-2 text-xs text-slate-400">Score: {q.answer.answer_score.toFixed(1)} / 10</p>
                  )}
                </li>
              ))}
          </ul>
        </section>
      )}
    </div>
  );
}
