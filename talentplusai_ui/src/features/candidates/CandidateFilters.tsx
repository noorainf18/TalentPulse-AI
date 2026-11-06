"use client";

type Props = {
  status: string;
  onStatusChange: (v: string) => void;
};

export default function CandidateFilters({ status, onStatusChange }: Props) {
  return (
    <div className="rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.85)] p-4 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md">
      <label className="flex max-w-md flex-col gap-2 text-base">
        <span className="font-medium text-slate-200">Status</span>
        <select
          className="rounded-lg border border-[rgba(0,230,200,0.18)] bg-[#0a1624]/90 px-3 py-2.5 text-base text-white outline-none ring-[rgba(0,230,195,0.35)] focus:ring-2"
          value={status}
          onChange={(e) => onStatusChange(e.target.value)}
        >
          <option value="">All</option>
          <option value="pending">Pending</option>
          <option value="screening_sent">Screening sent</option>
          <option value="borderline">Borderline</option>
          <option value="rejected">Rejected</option>
          <option value="hired">Hired</option>
        </select>
      </label>
    </div>
  );
}
