"use client";

import Link from "next/link";

import { aosFadeStagger } from "@/lib/aos";
import type { CandidateListItem } from "@/lib/types";
import { formatDate } from "@/lib/utils";

import { LabelBadge, StatusBadge } from "./StatusBadge";

export default function CandidateTable({ rows }: { rows: CandidateListItem[] }) {
  if (!rows.length) {
    return (
      <div
        className={`rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[#0d1e2e]/92 p-6 text-base text-slate-200 shadow-[0_10px_30px_rgba(0,0,0,0.35)] backdrop-blur-xl ${aosFadeStagger(2)}`}
      >
        No candidates found for selected filters.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[#0d1e2e]/92 shadow-[0_10px_30px_rgba(0,0,0,0.35)] backdrop-blur-xl">
      <table className="min-w-full text-base">
        <thead className="border-b border-[rgba(0,230,200,0.12)] bg-[#112234]/55 text-left text-sm font-semibold uppercase tracking-wide text-[rgba(159,255,230,0.55)]">
          <tr className={aosFadeStagger(2)}>
            <th className="px-4 py-3">Candidate</th>
            <th className="px-4 py-3">Score</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Label</th>
            <th className="px-4 py-3">Created</th>
            <th className="px-4 py-3">Action</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={row.id}
              className={`border-b border-[rgba(0,230,200,0.08)] last:border-0 hover:bg-[rgba(0,230,195,0.06)] ${aosFadeStagger(3 + i)}`}
            >
              <td className="px-4 py-3">
                <div className="font-medium text-white">{row.name}</div>
                <div className="text-sm text-slate-400">{row.email}</div>
              </td>
              <td className="px-4 py-3">
                <span className="bg-gradient-to-br from-[#00e6c8] to-[#5ee8ff] bg-clip-text font-semibold text-transparent">
                  {row.score ?? "—"}
                </span>
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={row.evaluation_status} />
              </td>
              <td className="px-4 py-3">
                <LabelBadge label={row.candidate_label} />
              </td>
              <td className="px-4 py-3 text-sm text-slate-400">{formatDate(row.created_at)}</td>
              <td className="px-4 py-3">
                <Link
                  href={`/candidates/${row.id}`}
                  className="font-medium text-[#00e6c8] hover:text-[#00ffc8] hover:underline"
                >
                  View
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
