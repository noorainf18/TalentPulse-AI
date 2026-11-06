"use client";

import { useMemo, useState } from "react";

import AosScope from "@/components/effects/AosScope";
import CandidateFilters from "@/features/candidates/CandidateFilters";
import CandidateTable from "@/features/candidates/CandidateTable";
import { useCandidates } from "@/features/candidates/useCandidates";
import { aosFadeStagger } from "@/lib/aos";

export default function CandidatesPage() {
  const [status, setStatus] = useState("");

  const filters = useMemo(
    () => ({
      status: status || undefined,
    }),
    [status],
  );

  const { data, isLoading, isError, error } = useCandidates(filters);

  return (
    <AosScope className="space-y-6">
      <section
        className={`relative overflow-hidden rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-6 shadow-[0_12px_32px_rgba(2,6,23,0.45)] backdrop-blur-md ${aosFadeStagger(0)}`}
      >
        <div className="absolute -right-16 -top-16 h-52 w-52 rounded-full bg-[rgba(0,230,200,0.08)] blur-3xl" />
        <div className="relative">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#9fffe6]">Talent Pool</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight text-white [font-family:var(--font-display)]">Candidate intelligence grid</h1>
          <p className="mt-2 text-base text-slate-300">All ingested candidates with screening status, score, and recruiter actions.</p>
        </div>
      </section>

      <div className={aosFadeStagger(1)}>
        <CandidateFilters status={status} onStatusChange={setStatus} />
      </div>

      {isLoading && (
        <div
          className={`rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-6 text-base text-slate-200 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md ${aosFadeStagger(2)}`}
        >
          Loading…
        </div>
      )}
      {isError && (
        <div
          className={`rounded-2xl border border-rose-300/35 bg-rose-900/30 p-6 text-base text-rose-100 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md ${aosFadeStagger(2)}`}
        >
          {(error as Error).message}
        </div>
      )}
      {data && <CandidateTable rows={data.results} />}
    </AosScope>
  );
}
