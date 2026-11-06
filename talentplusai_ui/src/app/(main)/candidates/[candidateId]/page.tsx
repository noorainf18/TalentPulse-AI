"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect } from "react";
import { toast } from "sonner";

import AosScope from "@/components/effects/AosScope";
import FeedbackForm from "@/features/evaluation/FeedbackForm";
import GapAnalysis from "@/features/evaluation/GapAnalysis";
import GithubEvidence from "@/features/evaluation/GithubEvidence";
import ParsedResumeView from "@/features/evaluation/ParsedResumeView";
import TraceTimeline from "@/features/evaluation/TraceTimeline";
import { useEvaluationDetail } from "@/features/evaluation/useEvaluationDetail";
import { useEvaluationSocket } from "@/features/evaluation/useEvaluationSocket";
import VoiceScreenPanel from "@/features/voice/VoiceScreenPanel";
import { useHash } from "@/hooks/useHash";
import { aosFadeStagger } from "@/lib/aos";

export default function CandidateDetailPage() {
  const params = useParams<{ candidateId: string }>();
  const candidateId = params?.candidateId ?? "";
  const { data, isLoading, isError, error } = useEvaluationDetail(candidateId);
  const tab = useHash();

  useEffect(() => {
    if (typeof window === "undefined" || !candidateId) return;
    if (!window.location.hash) {
      const url = `${window.location.pathname}${window.location.search}#profile`;
      window.history.replaceState(null, "", url);
    }
  }, [candidateId]);

  const onSocketError = useCallback(() => {
    toast.warning("Live updates disconnected. Polling continues.");
  }, []);

  useEvaluationSocket(candidateId, { onError: onSocketError });

  if (isLoading) {
    return <div className="text-base text-slate-300">Loading candidate…</div>;
  }
  if (isError || !data) {
    return <p className="text-base text-rose-200">{(error as Error)?.message ?? "Failed to load."}</p>;
  }

  if (data.kind === "pending") {
    return (
      <AosScope className="max-w-3xl space-y-4">
        <div
          id="profile"
          className={`rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-6 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md ${aosFadeStagger(0)}`}
        >
          <h1 className="text-2xl font-bold text-white">{data.candidate_name}</h1>
          <p className="mt-2 text-base text-slate-300">{data.message}</p>
          <p className="mt-4 text-sm text-[#9fffe6]">Screening in progress — this page refreshes automatically.</p>
        </div>
      </AosScope>
    );
  }

  const parsed =
    data.parsed_resume && typeof data.parsed_resume === "object"
      ? (data.parsed_resume as Record<string, unknown>)
      : null;

  return (
    <AosScope className="space-y-6">
      <div className={`scroll-mt-24 ${aosFadeStagger(0)}`}>
        <Link href="/candidates" className="text-base font-medium text-[#00e6c8] hover:text-[#00ffc8] hover:underline">
          ← Talent pool
        </Link>
        {tab !== "profile" ? (
          <h1 className="mt-2 text-3xl font-bold text-white">{data.candidate_name}</h1>
        ) : null}
      </div>

      {tab === "profile" && (
        <ParsedResumeView
          data={parsed}
          candidateName={data.candidate_name}
          overallScore={data.score_breakdown?.overall}
        />
      )}

      {tab === "evidence" && <GithubEvidence evidence={data.github_evidence} showHeading={false} />}

      {tab === "gaps" && <GapAnalysis analysis={data.gap_analysis} showHeading={false} />}

      {tab === "trace" && <TraceTimeline steps={data.trace_steps} showHeading={false} />}

      {tab === "feedback" && (
        <div className="space-y-6">
          <FeedbackForm
            candidateId={candidateId}
            initialThumbsUp={data.feedback_thumbs_up}
            initialNotes={data.feedback_notes}
            sectionClassName={aosFadeStagger(0)}
          />
          <section
            className={`rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-5 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md ${aosFadeStagger(1)}`}
          >
            <h3 className="mb-2 text-xl font-semibold text-white">Reasoning</h3>
            <p className="whitespace-pre-wrap text-[17px] leading-relaxed text-slate-300">{data.reasoning}</p>
          </section>
        </div>
      )}

      {tab === "voice" && (
        <VoiceScreenPanel
          candidateId={candidateId}
          evaluationId={data.id}
          initialInterview={data.voice_interview ?? null}
          sectionClassName={aosFadeStagger(0)}
        />
      )}
    </AosScope>
  );
}
