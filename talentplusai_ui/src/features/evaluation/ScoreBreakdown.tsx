import type { ScoreBreakdown as ScoreBreakdownType } from "@/lib/types";

export default function ScoreBreakdown({ score }: { score: ScoreBreakdownType }) {
  const bars = [
    { label: "Technical", value: score.technical },
    { label: "Culture", value: score.culture },
    { label: "Experience", value: score.experience },
  ];

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="mb-4 text-lg font-semibold text-slate-900">Score breakdown</h3>
      <div className="mb-5 flex items-end gap-2">
        <span className="text-4xl font-bold text-[#534ab7]">{score.overall}</span>
        <span className="mb-1 text-sm text-slate-500">/100 overall</span>
      </div>
      <div className="space-y-3">
        {bars.map((item) => (
          <div key={item.label}>
            <div className="mb-1 flex justify-between text-sm text-slate-700">
              <span>{item.label}</span>
              <span className="text-slate-500">{item.value}</span>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-100">
              <div
                className="h-2 rounded-full bg-gradient-to-r from-[#534ab7] to-[#1d9e75]"
                style={{ width: `${item.value}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
