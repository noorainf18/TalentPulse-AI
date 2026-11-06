import { aosFadeStagger } from "@/lib/aos";
import type { GapAnalysis as GapAnalysisType } from "@/lib/types";
import { cn } from "@/lib/utils";

function SkillChips({ label, skills, variant }: { label: string; skills: string[]; variant: "ok" | "miss" }) {
  if (!skills.length) {
    return (
      <p className="text-sm text-slate-300">
        {label}: none listed
      </p>
    );
  }
  const chip =
    variant === "ok"
      ? "border-[rgba(0,230,195,0.4)] bg-[rgba(18,59,69,0.5)] text-[#9fffe6]"
      : "border-rose-300/35 bg-rose-500/15 text-rose-100";
  return (
    <div className="mt-2">
      <p className="text-sm font-semibold text-slate-300">{label}</p>
      <div className="mt-1 flex flex-wrap gap-1.5">
        {skills.map((s) => (
          <span key={s} className={`rounded-md border px-2 py-0.5 text-sm font-medium ${chip}`}>
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function GapAnalysis({
  analysis,
  showHeading = true,
}: {
  analysis: GapAnalysisType | null;
  showHeading?: boolean;
}) {
  if (!analysis) {
    return (
      <section
        className={`rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-5 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md ${aosFadeStagger(1)}`}
      >
        {showHeading ? <h3 className="mb-2 text-xl font-semibold text-white">Fit &amp; gap analysis</h3> : null}
        <p className="text-base text-slate-300">No gap analysis available.</p>
      </section>
    );
  }

  const roleCards = analysis.top_role_matches ?? [];
  const roleCount = roleCards.length;
  const summaryAos = roleCount > 0 ? 2 + roleCount : 1;
  const gapsAos = summaryAos + 1;

  return (
    <section className="rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-5 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md">
      {showHeading ? <h3 className="mb-4 text-xl font-semibold text-white">Fit &amp; gap analysis</h3> : null}

      {roleCount > 0 ? (
        <div className="space-y-5">
          <p className={cn("text-sm font-semibold uppercase tracking-wide text-slate-300", aosFadeStagger(1))}>
            Role match details
          </p>
          {roleCards.map((rm, idx) => (
            <div
              key={`${rm.job_id}-${idx}`}
              className={cn("rounded-lg border border-[rgba(0,230,200,0.15)] bg-white/5 p-4", aosFadeStagger(2 + idx))}
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <div>
                  <p className="font-semibold text-white">{rm.role_title}</p>
                  <p className="text-base text-slate-300">
                    {rm.department} · {rm.seniority} · Job #{rm.job_id}
                  </p>
                </div>
                <p className="text-base font-medium text-slate-100">
                  Overall fit {Math.round((rm.overall_fit_score ?? 0) * 100)}%
                </p>
              </div>
              <p className="mt-2 text-base text-slate-200">
                <span className="text-slate-300">Hiring priority: </span>
                {rm.hiring_priority}
                <span className="text-slate-300"> · Min experience: </span>
                {rm.min_experience_years ?? 0} yrs
                <span className="text-slate-300"> · Fills critical gap: </span>
                {rm.fills_critical_team_gap ? "Yes" : "No"}
              </p>
              <p className="mt-2 text-base text-slate-200">
                <span className="text-slate-300">Tech focus: </span>
                {rm.tech_stack_focus}
              </p>
              <p className="mt-2 text-base text-slate-200">
                <span className="text-slate-300">Culture values: </span>
                {(rm.culture_values ?? []).join(", ") || "—"}
              </p>
              <p className="mt-2 text-sm text-slate-300">
                Required skills coverage: {Math.round((rm.required_skill_coverage ?? 0) * 100)}% · Preferred:{" "}
                {Math.round((rm.preferred_skill_coverage ?? 0) * 100)}%
              </p>
              <SkillChips label="Required matched" skills={rm.required_skills_matched ?? []} variant="ok" />
              <SkillChips label="Required missing" skills={rm.required_skills_missing ?? []} variant="miss" />
              <SkillChips label="Preferred matched" skills={rm.preferred_skills_matched ?? []} variant="ok" />
              <SkillChips label="Preferred missing" skills={rm.preferred_skills_missing ?? []} variant="miss" />
            </div>
          ))}
        </div>
      ) : null}

      <div className={cn(roleCount > 0 ? "mt-8" : "", "space-y-2 text-base text-slate-200", aosFadeStagger(summaryAos))}>
        <p>
          <span className="text-slate-300">Best role match: </span>
          <span className="font-semibold">{analysis.best_match_role || "—"}</span>
        </p>
        <p>
          <span className="text-slate-300">Department: </span>
          {analysis.best_match_department || "—"}
          <span className="text-slate-300"> · Best match fit: </span>
          {Math.round((analysis.best_match_fit_score ?? 0) * 100)}%
        </p>
        <p>
          <span className="text-slate-300">Fills team gap: </span>
          {analysis.fills_team_gap ? "Yes" : "No"}
        </p>
      </div>

      <div className={cn("mt-5 space-y-5", aosFadeStagger(gapsAos))}>
        {!!(analysis.candidate_skills ?? []).length && (
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-slate-300">Candidate skills</p>
            <p className="mt-2 text-base leading-relaxed text-slate-200">{(analysis.candidate_skills ?? []).join(", ")}</p>
          </div>
        )}

        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-300">Critical gaps</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {(analysis.critical_gaps ?? []).map((gap) => (
              <span
                key={gap}
                className="rounded-md border border-rose-300/35 bg-rose-500/15 px-2 py-1 text-sm font-medium text-rose-100"
              >
                {gap}
              </span>
            ))}
            {!(analysis.critical_gaps ?? []).length && (
              <span className="text-sm text-slate-300">No critical gaps identified.</span>
            )}
          </div>
        </div>

        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-300">Nice-to-have gaps</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {(analysis.nice_to_have_gaps ?? []).map((gap) => (
              <span
                key={gap}
                className="rounded-md border border-violet-300/35 bg-violet-500/15 px-2 py-1 text-sm font-medium text-violet-100"
              >
                {gap}
              </span>
            ))}
            {!(analysis.nice_to_have_gaps ?? []).length && (
              <span className="text-sm text-slate-300">None listed.</span>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
