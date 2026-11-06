"use client";

export default function IntegrationsPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-2xl font-bold text-slate-900">Integrations</h1>
      <p className="text-sm text-slate-600">
        Your screening pipeline already uses <strong>GitHub</strong> (research), <strong>Anthropic</strong> (parsing
        & scoring), <strong>Resend</strong> (email), and <strong>Supabase/Postgres</strong> (data). Configure keys in
        Django <code className="rounded bg-slate-100 px-1">.env</code>.
      </p>
      <ul className="list-inside list-disc text-sm text-slate-600">
        <li>MCP tools health: GET <code className="rounded bg-slate-100 px-1">/mcp/health/</code></li>
        <li>Admin / env: manage secrets server-side only</li>
      </ul>
    </div>
  );
}
