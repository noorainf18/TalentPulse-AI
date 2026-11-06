"use client";

import {
  Check,
  CircleDot,
  Headphones,
  Loader2,
  Mic,
  MicOff,
  PhoneOff,
  Shield,
  Video,
  Volume2,
} from "lucide-react";
import Link from "next/link";
import type { RefObject } from "react";
import { useMemo, useState } from "react";

import { TalentPlusLogo } from "@/components/brand/TalentPlusLogo";
import type { VoiceSessionBrief, VoiceSessionQuestionBrief } from "@/lib/types";

export type InterviewPhase = "idle" | "joining" | "connected" | "error";

type SidebarTab = "questions" | "timeline" | "highlights";

type Props = {
  phase: InterviewPhase;
  connLabel: string;
  micOn: boolean;
  hasToken: boolean;
  remoteAudioRef: RefObject<HTMLDivElement | null>;
  sessionBrief: VoiceSessionBrief | null;
  briefLoading: boolean;
  briefError: string | null;
  /** From LiveKit agent data packets — order preserved for staggered animation. */
  revealedQuestionIds: string[];
  /** After disconnect, show every question from the API (recap). */
  postCallRecap: boolean;
  onJoin: () => void;
  onToggleMic: () => void;
  onLeave: () => void;
  onRetry: () => void;
};

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function sortedQuestions(list: VoiceSessionQuestionBrief[]): VoiceSessionQuestionBrief[] {
  return [...list].sort((a, b) => a.sequence_order - b.sequence_order);
}

export default function CandidateInterviewLayout({
  phase,
  connLabel,
  micOn,
  hasToken,
  remoteAudioRef,
  sessionBrief,
  briefLoading,
  briefError,
  revealedQuestionIds,
  postCallRecap,
  onJoin,
  onToggleMic,
  onLeave,
  onRetry,
}: Props) {
  const [tab, setTab] = useState<SidebarTab>("questions");

  const roleTitle = sessionBrief?.role_title ?? "AI voice screening";
  const candidateName = sessionBrief?.candidate_display_name ?? "Candidate";
  const questions = useMemo(
    () => sortedQuestions(sessionBrief?.questions ?? []),
    [sessionBrief?.questions],
  );
  const answeredCount = questions.filter((q) => q.answered).length;

  const revealedSet = useMemo(() => new Set(revealedQuestionIds), [revealedQuestionIds]);

  const visibleQuestions = useMemo(() => {
    if (postCallRecap) return questions;
    if (phase === "connected") {
      return questions.filter((q) => revealedSet.has(q.id)).sort((a, b) => a.sequence_order - b.sequence_order);
    }
    return [];
  }, [questions, postCallRecap, phase, revealedSet]);

  const activeQuestionId = useMemo(() => {
    const pool = phase === "connected" && !postCallRecap ? visibleQuestions : questions;
    const next = pool.find((q) => !q.answered);
    return next?.id ?? pool[pool.length - 1]?.id ?? null;
  }, [questions, visibleQuestions, phase, postCallRecap]);

  const headline =
    phase === "connected"
      ? "Live session"
      : phase === "joining"
        ? "Connecting…"
        : phase === "error"
          ? "Session error"
          : "Ready when you are";

  const sessionDate = new Date().toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  const summaryLine =
    connLabel ||
    (phase === "idle"
      ? "The AI interviewer will ask role-specific questions. Speak clearly after each prompt."
      : "");

  return (
    <div className="relative z-10 mx-auto max-w-7xl px-4 pb-16 pt-8 sm:px-6 lg:px-8">
      <header className="mb-8 flex flex-col gap-4 lg:mb-10 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <Link
              href="/"
              className="inline-flex items-center gap-2 text-sm font-medium text-[#00e6c8] transition hover:text-[#9fffe6]"
            >
              <span aria-hidden>←</span> TalentPlus AI
            </Link>
            <span className="hidden h-4 w-px bg-white/15 sm:inline-block" aria-hidden />
            <div className="flex items-center gap-2">
              <TalentPlusLogo variant="mark" className="h-9 w-9 shrink-0 rounded-lg" />
              <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#9fffe6]/90">
                Voice screening
              </span>
            </div>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white [font-family:var(--font-display)] sm:text-3xl">
            {roleTitle}
          </h1>
          <p className="mt-1 text-sm text-slate-400">{candidateName}</p>
          {questions.length > 0 ? (
            <p className="mt-2 text-xs text-slate-500">
              Progress · {answeredCount} of {questions.length} answered
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2 lg:justify-end">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[rgba(0,230,200,0.2)] bg-[rgba(0,230,200,0.08)] px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-[#9fffe6]">
            <Shield className="h-3.5 w-3.5" aria-hidden />
            Encrypted
          </span>
          {phase === "connected" ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-red-400/35 bg-red-500/15 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-red-200">
              <Video className="h-3.5 w-3.5" aria-hidden />
              Live session
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/12 bg-white/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Not connected
            </span>
          )}
        </div>
      </header>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1.65fr)_minmax(300px,380px)] lg:items-start">
        {/* Left: stage + notes */}
        <div className="space-y-6">
          <div className="relative overflow-hidden rounded-3xl border border-[rgba(0,230,200,0.14)] bg-[rgba(13,30,46,0.92)] shadow-[0_24px_60px_rgba(2,6,23,0.55)] backdrop-blur-md">
            <div className="relative aspect-video min-h-[300px] w-full bg-gradient-to-br from-[#0a1f2e] via-[#061018] to-[#040c14]">
              <div className="absolute left-3 top-3 z-10 max-w-[55%] rounded-xl border border-white/10 bg-black/45 px-3 py-2 text-left text-xs font-medium text-white backdrop-blur-md sm:left-4 sm:top-4">
                <p className="text-[10px] uppercase tracking-wider text-[#9fffe6]/80">Interviewer</p>
                <p className="truncate text-sm">TalentPlus AI</p>
              </div>
              <div className="absolute right-3 top-3 z-10 flex items-center gap-2 rounded-xl border border-white/10 bg-black/45 px-3 py-2 text-xs font-medium text-white backdrop-blur-md sm:right-4 sm:top-4">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#00e6c8]/20 text-[11px] font-bold text-[#9fffe6]">
                  {initials(candidateName)}
                </span>
                <div className="min-w-0 pr-1">
                  <p className="text-[10px] uppercase tracking-wider text-slate-400">You</p>
                  <p className="max-w-[120px] truncate text-sm">{candidateName}</p>
                </div>
              </div>

              <div className="absolute inset-0 flex flex-col items-center justify-center px-6 pb-16 pt-10 text-center">
                <div className="relative mb-4 flex h-32 w-32 items-center justify-center sm:h-36 sm:w-36">
                  <div
                    className="absolute inset-0 rounded-full bg-gradient-to-br from-[#00e6c8]/22 via-cyan-500/10 to-transparent opacity-90 animate-tp-interview-ring"
                    aria-hidden
                  />
                  <div
                    className="absolute inset-2 rounded-full border border-[#00e6c8]/35 shadow-[0_0_36px_rgba(0,230,200,0.18)]"
                    aria-hidden
                  />
                  <div
                    className={`relative flex h-[5.5rem] w-[5.5rem] items-center justify-center rounded-full bg-gradient-to-br from-[#0d2838] to-[#061018] shadow-inner ring-1 ring-white/10 sm:h-24 sm:w-24 ${phase === "connected" ? "animate-pulse" : ""}`}
                    style={{
                      backgroundImage:
                        "linear-gradient(135deg, rgba(0,230,200,0.14) 0%, transparent 50%, rgba(0,255,200,0.06) 100%)",
                    }}
                  >
                    <TalentPlusLogo variant="mark" className="!h-14 !w-14 sm:!h-16 sm:!w-16" />
                  </div>
                </div>
                <h2 className="text-lg font-bold text-white sm:text-xl">{headline}</h2>
                {summaryLine ? (
                  <p className="mt-2 max-w-md text-pretty text-xs leading-relaxed text-slate-400 sm:text-sm">
                    {summaryLine}
                  </p>
                ) : null}
                {phase !== "connected" && phase !== "joining" ? (
                  <button
                    type="button"
                    onClick={onJoin}
                    disabled={!hasToken}
                    className="mt-6 inline-flex h-12 items-center justify-center gap-2 rounded-2xl border border-[rgba(0,230,195,0.5)] bg-gradient-to-r from-[#00e6c3] to-[#00ffc8] px-8 text-sm font-bold text-slate-950 shadow-[0_0_24px_rgba(0,230,195,0.3)] transition hover:brightness-105 disabled:opacity-50"
                  >
                    <CircleDot className="h-4 w-4" />
                    Enter interview room
                  </button>
                ) : null}
                {phase === "joining" ? (
                  <div className="mt-6 flex items-center gap-2 text-sm text-[#9fffe6]">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Joining…
                  </div>
                ) : null}
              </div>

              <div className="absolute bottom-0 left-0 right-0 z-10 flex justify-center px-4 pb-4">
                <div className="flex items-center gap-2 rounded-full border border-white/12 bg-black/50 px-3 py-2 shadow-lg backdrop-blur-md sm:gap-3 sm:px-5">
                  {phase === "connected" ? (
                    <>
                      <button
                        type="button"
                        onClick={onToggleMic}
                        className="flex h-10 w-10 items-center justify-center rounded-full border border-[rgba(0,230,195,0.35)] bg-white/5 text-white transition hover:bg-white/10"
                        aria-label={micOn ? "Mute microphone" : "Unmute microphone"}
                      >
                        {micOn ? (
                          <Mic className="h-5 w-5 text-[#9fffe6]" />
                        ) : (
                          <MicOff className="h-5 w-5 text-amber-300" />
                        )}
                      </button>
                      <span className="hidden h-6 w-px bg-white/15 sm:block" aria-hidden />
                      <button
                        type="button"
                        onClick={onLeave}
                        className="flex h-10 items-center gap-2 rounded-full bg-red-600/90 px-4 text-sm font-semibold text-white transition hover:bg-red-600"
                      >
                        <PhoneOff className="h-4 w-4" />
                        End
                      </button>
                    </>
                  ) : (
                    <span className="px-2 py-1 text-[11px] text-slate-500">
                      Mic &amp; end call unlock after you join
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div ref={remoteAudioRef} className="sr-only" aria-hidden />

          <div className="rounded-3xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.85)] p-6 shadow-[0_16px_40px_rgba(2,6,23,0.45)] backdrop-blur-md sm:p-7">
            <div className="mb-4 flex flex-wrap items-center gap-2 text-xs text-slate-400">
              <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
                {sessionDate}
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border border-[#00e6c8]/25 bg-[#00e6c8]/10 px-2.5 py-1 text-[#9fffe6]">
                Voice screening
              </span>
            </div>
            <h3 className="text-lg font-semibold text-white">Session notes · {roleTitle}</h3>
            <div className="mt-4 rounded-2xl border border-[#00e6c8]/20 bg-gradient-to-br from-[#00e6c8]/12 via-[rgba(13,30,46,0.6)] to-transparent p-4 sm:p-5">
              <p className="flex items-center gap-2 text-sm font-semibold text-[#9fffe6]">
                <TalentPlusLogo variant="mark" className="!h-8 !w-8 shrink-0" />
                AI session helper
              </p>
              <p className="mt-2 text-sm leading-relaxed text-slate-300">
                {phase === "connected"
                  ? "Listen for each question, then answer in a few clear sentences. Each question text appears in the list only after the AI has finished asking it."
                  : "After you join, questions unlock on the right one by one as the AI asks them. Headphones help reduce echo."}
              </p>
            </div>
          </div>

          {phase === "error" ? (
            <div className="text-center">
              <button
                type="button"
                onClick={onRetry}
                className="text-sm font-semibold text-[#9fffe6] underline decoration-[#00e6c8]/50 underline-offset-4 hover:text-white"
              >
                Try again
              </button>
            </div>
          ) : null}

          <p className="text-center text-xs leading-relaxed text-slate-600 lg:text-left">
            This call may be recorded for evaluation. Do not share your link — it is unique to you.
          </p>
        </div>

        {/* Right: tabs + list */}
        <aside className="space-y-4 lg:sticky lg:top-8">
          <div className="flex gap-1 rounded-2xl border border-white/10 bg-[rgba(6,15,22,0.65)] p-1">
            {(
              [
                { id: "questions" as const, label: "Question list" },
                { id: "timeline" as const, label: "Timeline" },
                { id: "highlights" as const, label: "Highlights" },
              ] as const
            ).map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={
                  tab === t.id
                    ? "flex-1 rounded-xl bg-[rgba(0,230,200,0.18)] py-2.5 text-center text-xs font-semibold text-[#9fffe6] sm:text-sm"
                    : "flex-1 rounded-xl py-2.5 text-center text-xs font-medium text-slate-500 transition hover:text-slate-300 sm:text-sm"
                }
              >
                {t.label}
              </button>
            ))}
          </div>

          {tab === "questions" ? (
            <div className="max-h-[min(70vh,640px)] space-y-3 overflow-y-auto rounded-3xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-4 shadow-[0_16px_40px_rgba(2,6,23,0.45)] backdrop-blur-md sm:p-5">
              {briefError ? (
                <p className="text-sm text-amber-200/90">{briefError}</p>
              ) : null}
              {briefLoading && questions.length === 0 ? (
                <div className="space-y-3" aria-busy>
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-24 animate-pulse rounded-2xl bg-white/5" />
                  ))}
                </div>
              ) : null}
              {!briefLoading && !briefError && questions.length === 0 ? (
                <p className="text-sm text-slate-400">
                  Questions will appear here shortly. If this stays empty, the session may still be preparing — try
                  refreshing in a moment.
                </p>
              ) : null}
              {!postCallRecap &&
              phase !== "connected" &&
              !briefLoading &&
              !briefError &&
              questions.length > 0 ? (
                <p className="text-sm text-slate-400">
                  Questions stay hidden until you join. During the call, each one appears in this list right after the AI
                  finishes asking it.
                </p>
              ) : null}
              {phase === "connected" && !postCallRecap && visibleQuestions.length === 0 && questions.length > 0 ? (
                <p className="text-sm text-slate-400">
                  Waiting for the first question… You&apos;ll see it here as soon as the interviewer finishes speaking it.
                </p>
              ) : null}
              {visibleQuestions.map((q, idx) => {
                const isActive = q.id === activeQuestionId && !q.answered;
                return (
                  <article
                    key={q.id}
                    style={{ animationDelay: `${idx * 70}ms` }}
                    className={
                      (isActive
                        ? "relative rounded-2xl border-2 border-[#00e6c8]/45 bg-[rgba(0,230,200,0.06)] p-4 shadow-[0_0_24px_rgba(0,230,200,0.12)] "
                        : "relative rounded-2xl border border-white/10 bg-[rgba(6,15,22,0.5)] p-4 ") +
                      "animate-tp-question-reveal"
                    }
                  >
                    <div className="flex items-start justify-between gap-3">
                      <span
                        className={
                          q.answered
                            ? "flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#00e6c8]/20 text-sm font-bold text-[#9fffe6]"
                            : "flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/15 bg-white/5 text-sm font-bold text-slate-300"
                        }
                      >
                        {String(q.sequence_order).padStart(2, "0")}
                      </span>
                      {q.answered ? (
                        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-300">
                          <Check className="h-4 w-4" strokeWidth={2.5} />
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-3 text-sm font-medium leading-snug text-white">{q.question_text}</p>
                    {q.answered && q.answer_preview ? (
                      <p className="mt-2 border-t border-white/10 pt-2 text-xs leading-relaxed text-slate-400">
                        {q.answer_preview}
                      </p>
                    ) : null}
                  </article>
                );
              })}
            </div>
          ) : null}

          {tab === "timeline" ? (
            <div className="rounded-3xl border border-white/10 bg-[rgba(13,30,46,0.75)] p-6 text-sm text-slate-400">
              A chronological timeline of this session will be available after processing completes.
            </div>
          ) : null}

          {tab === "highlights" ? (
            <div className="rounded-3xl border border-white/10 bg-[rgba(13,30,46,0.75)] p-6 text-sm text-slate-400">
              Highlight clips are not shown during the live interview. Recruiters may review recordings in the
              dashboard.
            </div>
          ) : null}

          <div className="rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.75)] p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#9fffe6]">Before you start</p>
            <ul className="mt-4 space-y-3 text-sm text-slate-300">
              <li className="flex gap-3">
                <Headphones className="mt-0.5 h-5 w-5 shrink-0 text-[#00e6c8]" />
                <span>Headphones reduce echo for the AI.</span>
              </li>
              <li className="flex gap-3">
                <Volume2 className="mt-0.5 h-5 w-5 shrink-0 text-[#00e6c8]" />
                <span>Check volume after joining.</span>
              </li>
              <li className="flex gap-3">
                <Mic className="mt-0.5 h-5 w-5 shrink-0 text-[#00e6c8]" />
                <span>Allow the microphone when your browser asks.</span>
              </li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}
