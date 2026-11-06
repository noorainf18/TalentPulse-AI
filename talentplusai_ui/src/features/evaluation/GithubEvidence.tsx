import { aosFadeStagger } from "@/lib/aos";
import type { GitHubEvidence as GitHubEvidenceType } from "@/lib/types";
import { cn } from "@/lib/utils";

function LangBars({ langs }: { langs: Record<string, number> }) {
  const entries = Object.entries(langs).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return null;
  return (
    <div className="mt-3">
      <p className="mb-2 text-sm font-semibold uppercase tracking-wide text-[rgba(159,255,230,0.9)]">Primary languages (usage)</p>
      <ul className="space-y-1 text-base text-slate-200">
        {entries.map(([lang, pct]) => (
          <li key={lang}>
            <span className="font-medium text-[#9fffe6]">{lang}</span>
            <span className="text-slate-300"> — {pct}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function GithubEvidence({
  evidence,
  showHeading = true,
}: {
  evidence: GitHubEvidenceType | null;
  showHeading?: boolean;
}) {
  if (!evidence) {
    return (
      <section
        className={`rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-5 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md ${aosFadeStagger(1)}`}
      >
        {showHeading ? <h3 className="mb-2 text-xl font-semibold text-white">Technical evidence</h3> : null}
        <p className="text-base text-slate-300">No GitHub evidence available.</p>
      </section>
    );
  }

  if (evidence.skipped) {
    return (
      <section
        className={`rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-5 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md ${aosFadeStagger(1)}`}
      >
        {showHeading ? <h3 className="mb-2 text-xl font-semibold text-white">Technical evidence</h3> : null}
        <p className="text-base text-slate-300">
          GitHub analysis was skipped
          {evidence.reason ? `: ${evidence.reason}` : "."}
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-5 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md">
      {showHeading ? <h3 className="mb-4 text-xl font-semibold text-white">Technical evidence</h3> : null}

      <div className={aosFadeStagger(1)}>
        <div className="space-y-2 text-base text-slate-200">
          <p>
            <span className="text-[#9fffe6]">Username: </span>
            {evidence.username ?? "—"}
          </p>
          {evidence.profile_url ? (
            <p>
              <span className="text-[#9fffe6]">Profile: </span>
              <a href={evidence.profile_url} className="font-medium text-[#00e6c8] hover:text-[#00ffc8] hover:underline" target="_blank" rel="noreferrer">
                {evidence.profile_url}
              </a>
            </p>
          ) : null}
          <p>
            <span className="text-violet-300">Recent commits (window): </span>
            <span className="font-semibold text-violet-100">{evidence.total_recent_commits ?? 0}</span>
          </p>
          <p>
            <span className="text-emerald-300">Original work signal: </span>
            <span className={evidence.has_original_work ? "font-semibold text-emerald-200" : "font-semibold text-amber-200"}>
              {evidence.has_original_work ? "Yes" : "No"}
            </span>
          </p>
          {evidence.error ? (
            <p className="rounded-lg border border-amber-300/35 bg-amber-500/15 px-3 py-2 text-base text-amber-100">
              <span className="font-medium">Note: </span>
              {evidence.error}
            </p>
          ) : null}
        </div>

        <LangBars langs={evidence.primary_languages ?? {}} />
      </div>

      {!!evidence.repos_analysed?.length && (
        <div className="mt-6 space-y-4">
          <p className={`text-sm font-semibold uppercase tracking-wide text-[rgba(159,255,230,0.9)] ${aosFadeStagger(2)}`}>
            Repositories analysed
          </p>
          {evidence.repos_analysed.map((repo, i) => (
            <div
              key={repo.name}
              className={cn("rounded-lg border border-[rgba(0,230,200,0.15)] bg-white/5 p-4", aosFadeStagger(3 + i))}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="font-semibold text-white">{repo.name}</div>
                  <div className="text-sm text-slate-300">
                    {repo.is_fork ? "Fork · " : ""}
                    {typeof repo.stars === "number" ? `${repo.stars} stars` : ""}
                  </div>
                </div>
              </div>
              <p className="mt-2 text-base text-slate-200">{repo.description || "No description"}</p>

              {Object.keys(repo.languages ?? {}).length > 0 ? (
                <div className="mt-3">
                  <p className="mb-1 text-sm font-semibold text-[rgba(159,255,230,0.9)]">Languages in repo</p>
                  <p className="text-base text-slate-200">
                    {Object.entries(repo.languages ?? {})
                      .sort((a, b) => b[1] - a[1])
                      .map(([l, n]) => `${l} (${n})`)
                      .join(", ")}
                  </p>
                </div>
              ) : null}

              {repo.readme_snippet ? (
                <div className="mt-3 rounded-md border border-[rgba(0,230,200,0.15)] bg-white/5 p-3">
                  <p className="mb-1 text-sm font-semibold text-violet-200/90">README excerpt</p>
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-200">{repo.readme_snippet}</p>
                </div>
              ) : null}

              <div className="mt-3 text-base text-slate-200">
                <p className="text-sm font-semibold text-emerald-200/90">Commit activity</p>
                <p>
                  Total commits fetched: {repo.commits?.total_commits_fetched ?? 0} · Recent (90d):{" "}
                  {repo.commits?.recent_commits_90_days ?? 0}
                </p>
                {!!repo.commits?.sample_messages?.length && (
                  <div className="mt-2">
                    <p className="text-sm text-slate-300">Sample messages</p>
                    <ul className="mt-1 list-inside list-disc space-y-0.5 text-sm text-slate-200">
                      {repo.commits.sample_messages.slice(0, 8).map((m, i) => (
                        <li key={i}>{m}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
