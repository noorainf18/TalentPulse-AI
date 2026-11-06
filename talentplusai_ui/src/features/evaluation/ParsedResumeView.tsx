import { cn } from "@/lib/utils";
import { aosFadeStagger } from "@/lib/aos";
import type { ReactNode } from "react";

type SkillGroup = {
  category: string;
  skills: string[];
};

type ExpItem = {
  company?: string;
  role?: string;
  duration?: string;
  duration_months?: number;
  location?: string | null;
  tech_stack?: string[];
  responsibilities?: string[];
  impact_metrics?: string[];
};

type ProjItem = {
  name?: string;
  tech_stack?: string[];
  description?: string;
  url?: string | null;
  highlights?: string[];
};

type EduItem = {
  institution?: string;
  degree?: string;
  field?: string;
  duration?: string;
  grade?: string | null;
};

function toTitleCase(value: string) {
  return value
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function getInitials(name: string) {
  const parts = name.split(/\s+/).filter(Boolean);
  if (!parts.length) return "NA";
  return parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("");
}

function uniq(items: string[]) {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of items) {
    const v = raw.trim();
    if (!v) continue;
    const key = v.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(v);
  }
  return out;
}

function SectionLabel({ title }: { title: string }) {
  return (
    <div className="mb-3 flex items-center gap-3">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-300">{title}</h3>
      <div className="h-px flex-1 bg-white/15" />
    </div>
  );
}

function Section({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return (
    <section className={cn("border-b border-white/10 py-5 last:border-0 last:pb-0 first:pt-0", className)}>
      <SectionLabel title={title} />
      {children}
    </section>
  );
}

function BulletList({ items }: { items: string[] }) {
  if (!items.length) return null;
  return (
    <ul className="mt-2 list-inside list-disc space-y-1.5 text-[15px] leading-relaxed text-slate-200">
      {items.map((line, i) => (
        <li key={i}>{line}</li>
      ))}
    </ul>
  );
}

function Tag({ text, tone = "blue" }: { text: string; tone?: "blue" | "teal" | "amber" | "violet" | "green" }) {
  const toneClass =
    tone === "teal"
      ? "border-teal-300/35 bg-teal-500/20 text-teal-100"
      : tone === "amber"
        ? "border-amber-300/35 bg-amber-500/20 text-amber-100"
        : tone === "violet"
          ? "border-violet-300/35 bg-violet-500/20 text-violet-100"
          : tone === "green"
            ? "border-emerald-300/35 bg-emerald-500/20 text-emerald-100"
            : "border-[rgba(0,230,195,0.34)] bg-[rgba(18,59,69,0.45)] text-[#9fffe6]";
  return <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${toneClass}`}>{text}</span>;
}

/** Returns up to 5 hero pill skills from the first skill group + experience tech stacks. */
function heroSkillPills(skillGroups: SkillGroup[], experience: ExpItem[]): string[] {
  const fromGroups = skillGroups.flatMap((g) => g.skills ?? []);
  const fromExp = experience.flatMap((e) => e.tech_stack ?? []);
  return uniq([...fromGroups, ...fromExp]).slice(0, 5);
}

/**
 * SkillsMatrixCard
 *
 * Renders skills exactly as categorized by the backend — no regex, no re-bucketing.
 * Each {category, skills[]} group from the resume becomes its own column/card.
 */
function SkillsMatrixCard({ skillGroups }: { skillGroups: SkillGroup[] }) {
  // Filter out empty groups
  const groups = skillGroups.filter((g) => g.skills && g.skills.length > 0);
  if (!groups.length) return null;

  // Pick a grid layout based on how many categories there are
  const gridClass =
    groups.length >= 3
      ? "grid-cols-1 md:grid-cols-2 xl:grid-cols-3"
      : groups.length === 2
        ? "grid-cols-1 sm:grid-cols-2"
        : "grid-cols-1";

  return (
    <div className="relative overflow-hidden rounded-2xl border border-[rgba(0,230,195,0.38)] bg-[rgba(8,22,32,0.72)] shadow-[0_0_48px_rgba(0,230,195,0.14),inset_0_1px_0_rgba(255,255,255,0.06)] backdrop-blur-xl">
      <div
        className="pointer-events-none absolute left-1/2 top-0 h-px w-[min(68%,420px)] -translate-x-1/2 bg-gradient-to-r from-transparent via-[#00ffc8] to-transparent opacity-95"
        aria-hidden
      />
      <div className="relative p-4 sm:p-5 md:p-6">
        <div className={cn("grid gap-6 lg:gap-8", gridClass)}>
          {groups.map((group) => (
            <div key={group.category} className="min-w-0">
              {/* Category heading — exactly as written in the resume */}
              <div className="mb-3 flex items-center gap-2 border-b border-[rgba(0,230,195,0.18)] pb-2.5">
                <span className="h-2 w-2 shrink-0 rounded-full bg-[#00ffc8] shadow-[0_0_8px_rgba(0,255,200,0.8)]" aria-hidden />
                <span className="text-sm font-semibold tracking-tight text-white">{group.category}</span>
              </div>
              {/* Skill pills */}
              <div className="flex flex-col gap-2">
                {uniq(group.skills).map((skill) => (
                  <div
                    key={skill}
                    className="flex items-center gap-2.5 rounded-lg border border-[rgba(0,230,195,0.26)] bg-[rgba(4,16,26,0.82)] px-3 py-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
                  >
                    <span
                      className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#00ffc8] shadow-[0_0_10px_rgba(0,255,200,0.9)]"
                      aria-hidden
                    />
                    <span className="min-w-0 text-[13px] font-medium leading-snug text-slate-100">{skill}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function summarizeText(summary: string) {
  const trimmed = summary.trim();
  if (!trimmed) return "";
  const pieces = trimmed.split(/(?<=[.!?])\s+/).filter(Boolean);
  return pieces.slice(0, 2).join(" ");
}

export default function ParsedResumeView({
  data,
  candidateName,
  overallScore,
}: {
  data: Record<string, unknown> | null;
  candidateName?: string;
  overallScore?: number | null;
}) {
  if (!data || typeof data !== "object" || Object.keys(data).length === 0) {
    return (
      <div className={`rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-6 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md ${aosFadeStagger(1)}`}>
        <p className="text-base text-slate-300">No parsed resume data is available for this candidate yet.</p>
      </div>
    );
  }

  const nameRaw = candidateName ?? (typeof data.name === "string" ? data.name : "Candidate");
  const summary = typeof data.summary === "string" ? summarizeText(data.summary) : "";
  const experience = Array.isArray(data.experience) ? (data.experience as ExpItem[]) : [];
  const projects = Array.isArray(data.projects) ? (data.projects as ProjItem[]) : [];
  const education = Array.isArray(data.education) ? (data.education as EduItem[]) : [];
  const certifications = Array.isArray(data.certifications)
    ? (data.certifications as string[]).filter((s) => typeof s === "string")
    : [];
  const achievements = Array.isArray(data.achievements)
    ? (data.achievements as string[]).filter((s) => typeof s === "string")
    : [];

  // skills is [{category, skills[]}] from the backend
  const skillGroups: SkillGroup[] = Array.isArray(data.skills)
    ? (data.skills as SkillGroup[]).filter(
        (g) => g && typeof g.category === "string" && Array.isArray(g.skills),
      )
    : [];

  const pills = heroSkillPills(skillGroups, experience);

  const displayName = toTitleCase(nameRaw);
  const initials = getInitials(displayName);
  const fit = typeof overallScore === "number" ? Math.max(0, Math.min(100, overallScore)) : null;
  const radius = 27;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = fit === null ? circumference : circumference * (1 - fit / 100);

  const expStart = skillGroups.length > 0 ? 4 : 3;
  const projBase = expStart + experience.length;
  const eduBase = projBase + projects.length;
  const certBase = eduBase + education.length;

  return (
    <div className="rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-6 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md">
      {/* ── Hero header ── */}
      <section className={cn("border-b border-white/10 pb-5", aosFadeStagger(1))}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-full border border-[rgba(0,230,195,0.35)] bg-[rgba(0,230,200,0.12)] text-base font-bold text-[#9fffe6]">
              {initials}
            </div>
            <div className="min-w-0">
              <h2 className="text-[32px] font-bold leading-[1.05] tracking-tight text-white [font-family:var(--font-display)]">
                {displayName}
              </h2>
            </div>
          </div>
          {fit !== null && (
            <div className="ml-2 shrink-0 text-center">
              <svg viewBox="0 0 64 64" className="h-16 w-16">
                <circle cx="32" cy="32" r={radius} fill="none" stroke="rgba(0,230,200,0.22)" strokeWidth="4" />
                <circle
                  cx="32" cy="32" r={radius} fill="none" stroke="url(#fitScoreGrad)"
                  strokeWidth="4" strokeLinecap="round"
                  strokeDasharray={circumference} strokeDashoffset={dashOffset}
                  transform="rotate(-90 32 32)"
                />
                <defs>
                  <linearGradient id="fitScoreGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#00e6c8" />
                    <stop offset="100%" stopColor="#5ee8ff" />
                  </linearGradient>
                </defs>
                <text x="32" y="31" textAnchor="middle" className="fill-white text-[12px] font-bold">{fit}</text>
                <text x="32" y="41" textAnchor="middle" className="fill-slate-300 text-[7px] uppercase tracking-wide">Fit</text>
              </svg>
            </div>
          )}
        </div>
        {pills.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {pills.map((skill, idx) => (
              <Tag key={skill} text={skill} tone={idx % 4 === 0 ? "blue" : idx % 4 === 1 ? "teal" : idx % 4 === 2 ? "amber" : "violet"} />
            ))}
          </div>
        )}
      </section>

      {/* ── Summary ── */}
      {summary && (
        <Section title="Summary" className={aosFadeStagger(2)}>
          <p className="border-l-[2.5px] border-[#00e6c8] pl-3 text-[15px] leading-[1.7] text-slate-100">{summary}</p>
        </Section>
      )}

      {/* ── Skills — rendered directly from backend categories ── */}
      {skillGroups.length > 0 && (
        <Section title="Skills" className={aosFadeStagger(3)}>
          <SkillsMatrixCard skillGroups={skillGroups} />
        </Section>
      )}

      {/* ── Experience ── */}
      {experience.length > 0 && (
        <Section title="Experience">
          <div className="space-y-4">
            {experience.map((ex, idx) => {
              const accent = idx === 0 ? "bg-[#00ffc8]" : "bg-[#00e6c8]";
              const impact = uniq(ex.impact_metrics ?? []);
              return (
                <div
                  key={idx}
                  className={cn("relative overflow-hidden rounded-xl border border-[rgba(0,230,200,0.15)] bg-white/5 p-4", aosFadeStagger(expStart + idx))}
                >
                  <span className={`absolute inset-y-0 left-0 w-[3px] ${accent}`} />
                  <div className="pl-2">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <p className="text-xl font-semibold text-white">{ex.role || "Role"}</p>
                      {ex.location && <p className="text-sm text-slate-300">{ex.location}</p>}
                    </div>
                    <p className="text-[15px] text-slate-300">
                      {ex.company}
                      {ex.duration ? ` · ${ex.duration}` : ""}
                      {typeof ex.duration_months === "number" ? ` · ${ex.duration_months} mo.` : ""}
                    </p>
                    <BulletList items={uniq(ex.responsibilities ?? [])} />
                    {impact.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {impact.map((m) => <Tag key={m} text={m} tone="green" />)}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Section>
      )}

      {/* ── Projects ── */}
      {projects.length > 0 && (
        <Section title="Projects">
          <div className="space-y-4">
            {projects.map((p, idx) => (
              <div key={idx} className={cn("rounded-lg border border-[rgba(0,230,200,0.15)] bg-white/5 p-4", aosFadeStagger(projBase + idx))}>
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="font-semibold text-white">{p.name || "Project"}</p>
                  {p.url && (
                    <a href={p.url} className="text-sm font-medium text-[#00e6c8] hover:text-[#00ffc8] hover:underline" target="_blank" rel="noreferrer">
                      Link
                    </a>
                  )}
                </div>
                {p.description && <p className="mt-2 text-[15px] text-slate-200">{p.description}</p>}
                {(p.tech_stack ?? []).length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {uniq(p.tech_stack ?? []).map((tech) => <Tag key={tech} text={tech} tone="blue" />)}
                  </div>
                )}
                <BulletList items={uniq(p.highlights ?? [])} />
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* ── Education ── */}
      {education.length > 0 && (
        <Section title="Education">
          <div className="space-y-3">
            {education.map((ed, idx) => (
              <div key={idx} className={cn("rounded-lg border border-[rgba(0,230,200,0.15)] bg-white/5 p-4 text-[15px]", aosFadeStagger(eduBase + idx))}>
                <p className="font-semibold text-white">{ed.degree} - {ed.field}</p>
                <p className="text-slate-300">
                  {ed.institution}{ed.duration ? ` · ${ed.duration}` : ""}
                </p>
                {ed.grade && <p className="mt-1 text-slate-300">Grade: {ed.grade}</p>}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* ── Certifications ── */}
      {certifications.length > 0 && (
        <Section title="Certifications" className={aosFadeStagger(certBase)}>
          <BulletList items={uniq(certifications)} />
        </Section>
      )}

      {/* ── Achievements ── */}
      {achievements.length > 0 && (
        <Section title="Achievements" className={aosFadeStagger(certBase + 1)}>
          <BulletList items={uniq(achievements)} />
        </Section>
      )}

      {/* Empty state */}
      {!summary && !experience.length && !projects.length && !education.length &&
       !certifications.length && !achievements.length && !skillGroups.length && (
        <p className="text-base text-slate-300">Parsed resume payload is empty.</p>
      )}
    </div>
  );
}