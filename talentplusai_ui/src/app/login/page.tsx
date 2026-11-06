"use client";

import { Eye, EyeOff } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { TalentPlusLogo } from "@/components/brand/TalentPlusLogo";
import NeuralBackground from "@/components/effects/NeuralBackground";
import { getCsrfToken, loginWithSession } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";

function LoginForm() {
  const router = useRouter();
  const sp = useSearchParams();
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);

  const nextUrl = sp.get("next") || "/dashboard";

  useEffect(() => {
    qc.invalidateQueries({ queryKey: ["auth", "me"] });
  }, [qc]);

  /**
   * Silently prime the CSRF cookie on mount.
   * Errors are intentionally swallowed — they will surface on submit
   * with a user-friendly message. We must NEVER show a toast here
   * because the user hasn't attempted anything yet.
   */
  useEffect(() => {
    getCsrfToken().catch(() => { /* silent — errors surface on submit */ });
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await loginWithSession(email, password);
      await qc.invalidateQueries({ queryKey: ["auth", "me"] });
      toast.success("Signed in successfully");
      router.replace(nextUrl.startsWith("/") ? nextUrl : "/dashboard");
    } catch (err) {
      const raw = (err as Error).message || "Login failed";
      // Show a friendly message when Django simply isn't running yet
      const isNetworkError =
        raw.toLowerCase().includes("failed to fetch") ||
        raw.toLowerCase().includes("network error") ||
        raw.toLowerCase().includes("networkerror") ||
        raw.toLowerCase().includes("reach the api");
      toast.error(
        isNetworkError
          ? "Cannot reach the server. Make sure Django is running on port 8000."
          : raw,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#060d14] text-[#e2f0f8]">
      <NeuralBackground />
      <div className="pointer-events-none fixed inset-0 z-[3]">
        <div className="absolute -top-32 left-1/4 h-[500px] w-[500px] rounded-full bg-cyan-500/[0.04] blur-[120px]" />
        <div className="absolute bottom-0 right-1/4 h-[400px] w-[400px] rounded-full bg-teal-400/[0.035] blur-[100px]" />
        <div className="absolute left-0 top-1/2 h-[300px] w-[300px] rounded-full bg-teal-500/[0.04] blur-[90px]" />
      </div>

      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-7xl flex-col px-6 py-8 lg:px-10">
        <Link
          href="/"
          className="mb-10 inline-flex w-fit items-center gap-3 rounded-lg transition-opacity hover:opacity-90"
          title="Back to TalentPlus AI"
        >
          <TalentPlusLogo variant="mark" className="h-10 w-10" />
          <span className="text-base font-semibold tracking-tight text-white">TalentPlus AI</span>
        </Link>

        <main className="mx-auto grid w-full max-w-6xl flex-1 items-center gap-10 lg:grid-cols-[1.3fr_0.9fr]">
          <section>
            <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-cyan-400/80">Workspace access</p>
            <h1 className="mt-3 max-w-3xl text-4xl font-extrabold leading-[1.08] tracking-tight text-white md:text-5xl">
              Sign in to your hiring workspace
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-[#e2f0f8]/72">
              Review AI-screened candidates, evidence traces, and TalentPlus GPT with your organization&apos;s credentials.
              Your session stays on the server — nothing sensitive is stored in the browser beyond standard secure cookies.
            </p>
            <ul className="mt-8 max-w-lg space-y-3 text-sm text-[#e2f0f8]/60">
              <li className="flex gap-2">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-cyan-400/80" />
                Session-aware authentication aligned with your Django backend
              </li>
              <li className="flex gap-2">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-cyan-400/80" />
                Same neural backdrop as the marketing site — tuned for focus, not distraction
              </li>
            </ul>
          </section>

          <section className="rounded-3xl border border-[rgba(0,230,200,0.12)] bg-[#0d1e2e]/88 p-7 shadow-[0_16px_48px_rgba(0,0,0,0.38)] backdrop-blur-xl md:p-8">
            <h2 className="text-3xl font-bold text-white">Sign in</h2>
            <p className="mt-2 text-base text-[#e2f0f8]/65">Use your admin credentials to continue.</p>
            <form onSubmit={onSubmit} className="mt-7 space-y-5">
              <div>
                <label htmlFor="email" className="mb-2 block text-sm font-semibold uppercase tracking-wide text-[#e2f0f8]/65">
                  Email address
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="username"
                  placeholder="admin@talentplus.ai"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-base text-slate-950 outline-none placeholder:text-slate-400 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-400/35"
                  required
                />
              </div>

              <div>
                <label htmlFor="password" className="mb-2 block text-sm font-semibold uppercase tracking-wide text-[#e2f0f8]/65">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-white py-3 pl-4 pr-20 text-base text-slate-950 outline-none placeholder:text-slate-400 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-400/35"
                    required
                  />
                  <button
                    type="button"
                    tabIndex={-1}
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md px-2 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  >
                    {showPassword ? (
                      <span className="inline-flex items-center gap-1.5">
                        <EyeOff className="h-4 w-4 shrink-0" aria-hidden />
                        Hide
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5">
                        <Eye className="h-4 w-4 shrink-0" aria-hidden />
                        Show
                      </span>
                    )}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={busy}
                className="w-full rounded-xl bg-gradient-to-r from-cyan-400 to-teal-500 py-3.5 text-base font-bold text-slate-950 shadow-[0_8px_24px_rgba(34,211,238,0.35)] transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {busy ? "Signing in..." : "Get started"}
              </button>
            </form>
          </section>
        </main>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-[#060d14] text-base text-[#e2f0f8]/75">
          Loading…
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
