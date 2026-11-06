import type { CandidateLabel, EvaluationStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const statusColor: Record<EvaluationStatus, string> = {
  pending: "bg-slate-500/15 text-slate-200 border-slate-300/25",
  screening_sent: "bg-emerald-400/20 text-emerald-100 border-emerald-300/35",
  rejected: "bg-rose-400/20 text-rose-100 border-rose-300/35",
  borderline: "bg-amber-400/20 text-amber-100 border-amber-300/35",
  hired: "bg-sky-400/20 text-sky-100 border-sky-300/35",
};

export function StatusBadge({ status }: { status: EvaluationStatus }) {
  return (
    <span className={cn("rounded-md border px-2 py-1 text-sm capitalize", statusColor[status])}>
      {status.replace("_", " ")}
    </span>
  );
}

export function LabelBadge({ label }: { label: CandidateLabel }) {
  return (
    <span className="rounded-md border border-violet-300/35 bg-violet-400/20 px-2 py-1 text-sm font-medium text-violet-100">
      {label}
    </span>
  );
}
