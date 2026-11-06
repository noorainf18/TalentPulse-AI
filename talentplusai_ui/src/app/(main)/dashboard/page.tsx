"use client";

import Link from "next/link";

import { useDashboardSummary } from "@/features/dashboard/useDashboardSummary";
import { formatDate } from "@/lib/utils";

export default function DashboardPage() {
  const { data, isLoading, isError, error } = useDashboardSummary();

  const kpis = data?.kpis;
  const recent = data?.recent_activity ?? [];
  const pipeline = kpis
    ? [
        { label: "Applied", value: kpis.total_candidates },
        { label: "AI screened", value: Math.max(kpis.total_candidates - kpis.pending, 0) },
        { label: "Reviewed", value: Math.max(kpis.total_candidates - (kpis.pending + kpis.hired + kpis.rejected), 0) },
        { label: "Shortlisted", value: kpis.review_queue },
        { label: "Offered", value: kpis.hired },
      ]
    : [];
  const maxPipe = Math.max(...pipeline.map((p) => p.value), 1);

  function pipelineBarPct(value: number) {
    if (maxPipe <= 0) return 0;
    if (value <= 0) return 2;
    return Math.max((value / maxPipe) * 100, 10);
  }

  return (
    <div className="mx-auto max-w-5xl space-y-7 py-3">

      <section className="fade-up fade-up-1 hero-card relative overflow-hidden rounded-2xl border border-emerald-500/20 bg-[#0d1e2e]/80 p-8 shadow-[0_0_0_1px_rgba(52,211,153,0.1),0_20px_60px_rgba(0,0,0,0.5)] backdrop-blur-2xl">
        <div className="pointer-events-none absolute -right-20 -top-20 h-72 w-72 rounded-full bg-emerald-500/[0.07] blur-3xl hero-orb-1" />
        <div className="pointer-events-none absolute -bottom-10 right-40 h-48 w-48 rounded-full bg-green-500/[0.06] blur-2xl hero-orb-2" />
        <div className="absolute bottom-0 right-24 top-0 w-px -rotate-[18deg] bg-gradient-to-b from-transparent via-emerald-400/22 to-transparent" />
        <div className="absolute bottom-0 right-44 top-0 w-px -rotate-[18deg] bg-gradient-to-b from-transparent via-lime-400/18 to-transparent" />

        <div className="relative">
          <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-emerald-400">Hiring Intelligence Dashboard</p>
          <h1 className="mt-2 bg-gradient-to-br from-white via-emerald-100 to-lime-200 bg-clip-text text-4xl font-extrabold leading-tight tracking-tight text-transparent [font-family:var(--font-display)]">
            Global hiring intelligence
            <br />
            for high-growth teams
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#e2f0f8]/72">
            TalentPlus AI parses resumes, maps technical evidence, and produces structured fit-gap decisions in one secure workflow.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/upload"
              className="upload-btn relative overflow-hidden rounded-xl bg-gradient-to-r from-cyan-400 to-teal-400 px-5 py-2.5 text-sm font-bold text-slate-950 shadow-[0_0_20px_rgba(34,211,238,0.4)] transition-all duration-300 hover:scale-[1.05] hover:shadow-[0_0_40px_rgba(34,211,238,0.7)] active:scale-95"
            >
              <span className="relative z-10">Upload CV</span>
              <span className="btn-shimmer pointer-events-none absolute inset-0" />
            </Link>
            <Link
              href="/candidates"
              className="rounded-xl border border-emerald-400/25 bg-white/5 px-5 py-2.5 text-sm font-medium text-emerald-300 backdrop-blur-sm transition-all duration-200 hover:border-emerald-400/50 hover:bg-emerald-400/10 hover:text-white hover:shadow-[0_0_16px_rgba(52,211,153,0.2)]"
            >
              Browse talent pool
            </Link>
          </div>
        </div>
      </section>

      {isLoading && (
        <div className="fade-up fade-up-2 rounded-2xl border border-cyan-400/12 bg-[#0d1e2e]/92 p-6 text-sm text-slate-300 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-emerald-500/35 border-t-emerald-400" />
            Loading dashboard summary…
          </div>
        </div>
      )}

      {isError && (
        <div className="fade-up fade-up-2 rounded-2xl border border-rose-400/30 bg-rose-900/20 p-6 text-sm text-rose-200 backdrop-blur-xl">
          {(error as Error)?.message ?? "Failed to load dashboard summary."}
        </div>
      )}

      {!!kpis && (
        <section className="fade-up fade-up-2 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[
            { label: "Total candidates", value: kpis.total_candidates, icon: "👥" },
            { label: "Pending", value: kpis.pending, icon: "⏳" },
            { label: "Review queue", value: kpis.review_queue, icon: "📋" },
            { label: "Hired", value: kpis.hired, icon: "✅" },
            { label: "Rejected", value: kpis.rejected, icon: "❌" },
            { label: "Average score", value: kpis.avg_score ?? "—", icon: "📊" },
          ].map((item, i) => (
            <div key={item.label} className={`kpi-card fade-up fade-up-${Math.min(i + 2, 6)} group rounded-2xl border border-cyan-400/15 bg-[#0d1e2e]/80 p-5 backdrop-blur-2xl`}>
              <div className="flex items-start justify-between">
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400 transition-colors group-hover:text-cyan-400/80">
                  {item.label}
                </p>
                <span className="text-xl opacity-60 transition-transform duration-300 group-hover:scale-125 group-hover:opacity-90">{item.icon}</span>
              </div>
              <p className="mt-2 bg-gradient-to-br from-cyan-300 via-cyan-400 to-teal-400 bg-clip-text text-[1.9rem] font-extrabold tracking-tight text-transparent [font-family:var(--font-display)] drop-shadow-[0_0_20px_rgba(34,211,238,0.28)]">
                {item.value}
              </p>
              <div className="mt-3 h-px bg-gradient-to-r from-transparent via-emerald-400/0 to-transparent transition-all duration-300 group-hover:via-emerald-400/45" />
            </div>
          ))}
        </section>
      )}

      {!!kpis && (
        <section className="fade-up fade-up-4 space-y-3">
          <p className="flex items-center gap-3 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400">
            Hiring pipeline
            <span className="h-px flex-1 bg-gradient-to-r from-slate-600/80 to-transparent" />
          </p>
          <div className="overflow-hidden rounded-2xl border border-slate-600/60 bg-[#111827]/95 shadow-[0_8px_30px_rgba(0,0,0,0.4)] md:grid md:grid-cols-5">
            {pipeline.map((step) => (
              <div
                key={step.label}
                className="pipe-step group border-b border-slate-700/80 px-4 py-5 transition-colors last:border-b-0 md:border-b-0 md:border-r md:border-slate-700/80 md:last:border-r-0"
              >
                <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-slate-400 group-hover:text-slate-300">{step.label}</p>
                <p
                  className="mt-1 text-2xl font-extrabold tabular-nums tracking-tight text-[#00f5ff] [font-family:var(--font-display)] [text-shadow:0_0_18px_rgba(0,245,255,0.45)] transition-all duration-200"
                >
                  {step.value}
                </p>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800/90">
                  <div
                    className="pipe-bar h-full rounded-full bg-[#39FF14] shadow-[0_0_12px_rgba(57,255,20,0.55)]"
                    style={{ width: `${pipelineBarPct(step.value)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="fade-up fade-up-5 rounded-2xl border border-slate-600/60 bg-[#111827]/95 p-6 shadow-[0_10px_40px_rgba(0,0,0,0.35)] backdrop-blur-xl">
        <div className="mb-5 flex items-center justify-between gap-2">
          <h2 className="text-lg font-bold text-white [font-family:var(--font-display)]">Recent activity</h2>
          <Link
            href="/candidates"
            className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#39FF14] transition-all hover:text-[#5cff5c] hover:drop-shadow-[0_0_10px_rgba(57,255,20,0.5)]"
          >
            Open talent pool →
          </Link>
        </div>

        {!recent.length ? (
          <p className="text-sm text-slate-400">
            No candidates yet. Start from{" "}
            <Link href="/upload" className="font-medium text-[#39FF14] hover:underline">
              Ingestion
            </Link>{" "}
            to upload resumes.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-600/50 bg-[#0f172a]/90">
            <table className="min-w-full text-sm">
              <thead className="border-b border-slate-700/80 bg-[#1e293b]/50 text-left">
                <tr>
                  {["Candidate", "Status", "Score", "Created", "Action"].map((h) => (
                    <th key={h} className="px-4 py-3 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recent.map((row, i) => (
                  <tr
                    key={row.candidate_id}
                    className={`activity-row border-b border-slate-700/50 last:border-0 fade-up fade-up-${Math.min(i + 1, 6)} hover:bg-slate-800/40`}
                  >
                    <td className="px-4 py-3.5">
                      <div className="font-semibold text-white">{row.name}</div>
                      <div className="text-xs text-slate-400">{row.email}</div>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="inline-flex items-center rounded-full border border-[#39FF14]/65 bg-[#39FF14]/[0.07] px-2.5 py-0.5 text-xs font-semibold capitalize text-[#39FF14] [text-shadow:0_0_12px_rgba(57,255,20,0.25)]">
                        {row.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="text-base font-bold tabular-nums text-[#00f5ff] outline-none [text-shadow:0_0_14px_rgba(0,245,255,0.35)]">
                        {row.score ?? "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-400">{formatDate(row.created_at)}</td>
                    <td className="px-4 py-3.5">
                      <Link
                        href={`/candidates/${row.candidate_id}`}
                        className="text-xs font-bold uppercase tracking-[0.12em] text-[#39FF14] transition-all duration-200 hover:text-[#5cff5c] hover:drop-shadow-[0_0_10px_rgba(57,255,20,0.55)]"
                      >
                        View →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <style>{`
        @keyframes fadeUp {
          from {
            opacity: 0;
            transform: translateY(24px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .fade-up {
          animation: fadeUp 0.55s cubic-bezier(0.22, 1, 0.36, 1) both;
        }
        .fade-up-1 {
          animation-delay: 0.05s;
        }
        .fade-up-2 {
          animation-delay: 0.12s;
        }
        .fade-up-3 {
          animation-delay: 0.2s;
        }
        .fade-up-4 {
          animation-delay: 0.28s;
        }
        .fade-up-5 {
          animation-delay: 0.36s;
        }
        .fade-up-6 {
          animation-delay: 0.44s;
        }

        .hero-orb-1 {
          animation: floatA 9s ease-in-out infinite;
        }
        .hero-orb-2 {
          animation: floatB 11s ease-in-out infinite;
        }
        @keyframes floatA {
          0%,
          100% {
            transform: translate(0, 0);
          }
          50% {
            transform: translate(-14px, 10px);
          }
        }
        @keyframes floatB {
          0%,
          100% {
            transform: translate(0, 0);
          }
          50% {
            transform: translate(10px, -12px);
          }
        }

        .kpi-card {
          transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
        }
        .kpi-card:hover {
          transform: translateY(-4px) scale(1.015);
          box-shadow:
            0 0 0 1px rgba(52, 211, 153, 0.32),
            0 16px 40px rgba(0, 0, 0, 0.5),
            0 0 30px rgba(52, 211, 153, 0.12);
          border-color: rgba(52, 211, 153, 0.4) !important;
        }

        .activity-row {
          position: relative;
          transition: background 0.2s;
        }
        .activity-row::after {
          content: "";
          position: absolute;
          inset: 0;
          background: linear-gradient(90deg, transparent, rgba(57, 255, 20, 0.06), transparent);
          opacity: 0;
          transition: opacity 0.3s;
          pointer-events: none;
        }
        .activity-row:hover::after {
          opacity: 1;
        }

        @keyframes barFill {
          from {
            width: 12% !important;
          }
        }
        .pipe-bar {
          animation: barFill 1.2s cubic-bezier(0.22, 1, 0.36, 1) both;
        }

        .btn-shimmer {
          background: linear-gradient(110deg, transparent 25%, rgba(255, 255, 255, 0.35) 50%, transparent 75%);
          background-size: 200% 100%;
          animation: shimmer 2.4s infinite linear;
        }
        @keyframes shimmer {
          0% {
            background-position: 200% 0;
          }
          100% {
            background-position: -200% 0;
          }
        }
      `}</style>
    </div>
  );
}
