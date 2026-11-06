"use client";

import { Bot, CheckCircle, Github, History, LayoutDashboard, LogOut, Mic, Search, Target, Upload, User } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ComponentType, CSSProperties, ReactNode } from "react";
import { useEffect, useRef, useState } from "react";

import { TalentPlusLogo } from "@/components/brand/TalentPlusLogo";
import NeuralBackground from "@/components/effects/NeuralBackground";
import { useSession } from "@/features/auth/useSession";
import { useHash } from "@/hooks/useHash";
import { logoutSession } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";

function candidateDetailSecondary(pathname: string) {
  const m = /^\/candidates\/([0-9a-f-]{36})$/i.exec(pathname);
  if (!m) return null;
  const id = m[1];
  const base = `/candidates/${id}`;
  const links: { href: string; label: string; hash: string; icon: ComponentType<{ className?: string }> }[] = [
    { href: `${base}#profile`, hash: "profile", label: "Candidate profile", icon: User },
    { href: `${base}#evidence`, hash: "evidence", label: "Technical evidence", icon: Github },
    { href: `${base}#gaps`, hash: "gaps", label: "Fit & gap analysis", icon: Target },
    { href: `${base}#trace`, hash: "trace", label: "Execution trace", icon: History },
    { href: `${base}#feedback`, hash: "feedback", label: "Review / feedback", icon: CheckCircle },
    { href: `${base}#voice`, hash: "voice", label: "Voice screen", icon: Mic },
  ];
  return links;
}

/** Landing-aligned nav: dark teal shell, neon teal active/hover (talentplus-landing). */
const NAV_ACTIVE =
  "active-nav border-[rgba(0,230,195,0.45)] bg-[rgba(15,42,51,0.92)] shadow-[0_0_0_1px_rgba(0,230,195,0.25),0_0_18px_rgba(0,230,195,0.28),inset_0_0_16px_rgba(0,230,195,0.08)]";
const NAV_INACTIVE =
  "border border-transparent text-slate-300/80 hover:border-[rgba(0,230,195,0.28)] hover:bg-[rgba(18,59,69,0.42)] hover:text-white";
const NAV_ICON_ACTIVE = "text-[#9fffe6] drop-shadow-[0_0_8px_rgba(0,255,200,0.55)]";
const NAV_ICON_IDLE = "text-slate-400 group-hover:text-[#9fffe6]";
const NAV_DOT = "bg-[#00ffc8] shadow-[0_0_10px_rgba(0,255,200,0.65)]";
const NAV_BAR_STYLE = { "--tab-bar": "#00e6c3", "--tab-bar-glow": "rgba(0, 255, 200, 0.65)" } as CSSProperties;

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const qc = useQueryClient();
  const { data: me } = useSession();
  const [accountOpen, setAccountOpen] = useState(false);
  const accountRef = useRef<HTMLDivElement>(null);
  const secondary = candidateDetailSecondary(pathname);
  /** Candidate workspace (`/candidates/:id`): hide header Upload CV per UX. */
  const hideUploadCv = Boolean(secondary);
  const hash = useHash();

  useEffect(() => {
    function closeOnOutside(e: MouseEvent) {
      const target = e.target as Node | null;
      if (!target) return;
      if (!accountRef.current?.contains(target)) setAccountOpen(false);
    }
    if (accountOpen) document.addEventListener("click", closeOnOutside);
    return () => document.removeEventListener("click", closeOnOutside);
  }, [accountOpen]);

  async function handleLogout() {
    try {
      await logoutSession();
    } catch {
      /* still clear client */
    }
    await qc.invalidateQueries({ queryKey: ["auth", "me"] });
    router.replace("/login");
  }

  return (
    <>
      {/* Neural canvas must sit INSIDE a parent without an opaque bg, or the full-bleed
          page background on the shell would paint over the fixed canvas and hide the network. */}
      <div className="relative flex min-h-screen overflow-hidden text-slate-100">
        <NeuralBackground />
        <div className="pointer-events-none fixed inset-0 z-[3]">
          <div className="absolute -top-32 left-1/4 h-[500px] w-[500px] rounded-full bg-[rgba(0,230,200,0.06)] blur-[120px]" />
          <div className="absolute bottom-0 right-1/4 h-[400px] w-[400px] rounded-full bg-[rgba(0,230,195,0.05)] blur-[100px]" />
          <div className="absolute left-0 top-1/2 h-[300px] w-[300px] rounded-full bg-[rgba(0,230,200,0.05)] blur-[90px]" />
        </div>

        <aside className="relative z-20 flex w-16 shrink-0 flex-col items-center border-r border-[rgba(0,230,200,0.12)] bg-[#0d1e2e]/82 py-4 backdrop-blur-xl">
          <Link href="/dashboard" className="mb-6 block p-1 transition-transform hover:scale-110" title="Home">
            <TalentPlusLogo variant="mark" className="rounded-lg drop-shadow-[0_0_14px_rgba(0,230,195,0.45)]" />
          </Link>
        </aside>

        <aside className="relative z-20 flex w-56 shrink-0 flex-col border-r border-[rgba(0,230,200,0.12)] bg-[#0d1e2e]/78 px-3 py-5 backdrop-blur-xl">
          <p className="mb-3 px-2 text-[10px] font-bold uppercase tracking-[0.2em] text-[rgba(0,230,195,0.65)]">Workspace</p>

          {secondary ? (
            <nav className="flex flex-col gap-0.5">
              {secondary.map(({ href, label, hash: tabHash, icon: Icon }) => {
                const active = hash === tabHash;
                return (
                  <a
                    key={href}
                    href={href}
                    className={cn(
                      "nav-item group flex items-center gap-2.5 rounded-xl px-2.5 py-2 text-sm transition-all duration-200",
                      active ? cn("border font-semibold text-white", NAV_ACTIVE) : NAV_INACTIVE,
                    )}
                    style={active ? NAV_BAR_STYLE : undefined}
                  >
                    <Icon className={cn("h-4 w-4 shrink-0 transition-all duration-200", active ? NAV_ICON_ACTIVE : NAV_ICON_IDLE)} />
                    <span className="leading-none">{label}</span>
                    {active && <span className={cn("ml-auto h-1.5 w-1.5 rounded-full", NAV_DOT)} />}
                  </a>
                );
              })}
            </nav>
          ) : (
            <nav className="flex flex-col gap-0.5">
              {[
                { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
                { href: "/upload", label: "Ingestion", icon: Upload },
                { href: "/candidates", label: "Talent pool", icon: Search },
                { href: "/chatbot", label: "Chat Bot", icon: Bot },
              ].map(({ href, label, icon: Icon }) => {
                const active = href === "/candidates" ? pathname.startsWith("/candidates") : pathname === href;
                return (
                  <Link
                    key={href}
                    href={href}
                    className={cn(
                      "nav-item group flex items-center gap-2.5 rounded-xl px-2.5 py-2 text-sm transition-all duration-200",
                      active ? cn("border font-semibold text-white", NAV_ACTIVE) : NAV_INACTIVE,
                    )}
                    style={active ? NAV_BAR_STYLE : undefined}
                  >
                    <Icon className={cn("h-4 w-4 shrink-0 transition-all duration-200", active ? NAV_ICON_ACTIVE : NAV_ICON_IDLE)} />
                    <span className="leading-none">{label}</span>
                    {active && <span className={cn("ml-auto h-1.5 w-1.5 rounded-full", NAV_DOT)} />}
                  </Link>
                );
              })}
            </nav>
          )}

          <div className="mt-auto h-px bg-gradient-to-r from-transparent via-[rgba(0,230,195,0.35)] to-transparent" />
        </aside>

        <div className="relative z-10 flex min-w-0 flex-1 flex-col">
          <header className="relative z-30 flex h-14 items-center justify-end border-b border-[rgba(0,230,200,0.12)] bg-[#0d1e2e]/72 px-6 backdrop-blur-xl">
            <div className="flex items-center gap-3">
              {!hideUploadCv && (
                <Link
                  href="/upload"
                  className="upload-btn relative overflow-hidden rounded-xl border border-[rgba(0,230,195,0.45)] bg-gradient-to-r from-[#00e6c3] to-[#00ffc8] px-5 py-2 text-sm font-bold text-slate-950 shadow-[0_0_18px_rgba(0,230,195,0.35)] transition-all duration-300 hover:scale-[1.04] hover:shadow-[0_0_28px_rgba(0,255,200,0.55)] active:scale-95"
                >
                  <span className="relative z-10">Upload CV</span>
                  <span className="btn-shimmer pointer-events-none absolute inset-0" />
                </Link>
              )}

              <div className="relative" ref={accountRef}>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setAccountOpen((o) => !o);
                  }}
                  title="Account"
                  aria-expanded={accountOpen}
                  aria-haspopup="menu"
                  className="flex h-9 w-9 items-center justify-center rounded-full border border-[rgba(0,230,195,0.4)] bg-[rgba(0,230,200,0.1)] text-[#9fffe6] shadow-[0_0_12px_rgba(0,230,195,0.28)] transition-all duration-200 hover:scale-110 hover:bg-[rgba(0,230,200,0.18)] hover:shadow-[0_0_20px_rgba(0,255,200,0.4)]"
                >
                  <User className="h-4 w-4" strokeWidth={2} />
                </button>

                {accountOpen && (
                  <div
                    role="menu"
                    className="absolute right-0 z-[120] mt-2 w-56 rounded-2xl border border-[rgba(0,230,200,0.18)] bg-[#0d1e2e]/92 py-1 shadow-[0_20px_60px_rgba(0,0,0,0.6),0_0_40px_rgba(0,230,195,0.12)] backdrop-blur-2xl"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="border-b border-white/10 px-4 py-3">
                      <p className="text-[10px] font-semibold uppercase tracking-widest text-[rgba(0,230,195,0.7)]">Signed in</p>
                      <p className="mt-0.5 truncate text-sm font-semibold text-white">{me?.email ?? "—"}</p>
                    </div>
                    <button
                      type="button"
                      role="menuitem"
                      className="flex w-full items-center gap-2.5 px-4 py-3 text-left text-sm text-slate-200 transition-colors hover:bg-white/8 hover:text-white"
                      onClick={() => {
                        setAccountOpen(false);
                        void handleLogout();
                      }}
                    >
                      <LogOut className="h-4 w-4 text-slate-400" />
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            </div>
          </header>

          <main className="relative flex-1 overflow-auto">
            <div className="relative z-10 p-6">{children}</div>
          </main>
        </div>
      </div>

      <style>{`
        .nav-item {
          position: relative;
        }
        .nav-item::before {
          content: "";
          position: absolute;
          left: 0;
          top: 20%;
          bottom: 20%;
          width: 2px;
          border-radius: 2px;
          background: var(--tab-bar, #00e6c3);
          box-shadow: 0 0 8px 2px var(--tab-bar-glow, rgba(0, 255, 200, 0.65));
          opacity: 0;
          transform: scaleY(0);
          transition: transform 0.2s ease, opacity 0.2s ease;
        }
        .nav-item:hover::before,
        .active-nav::before {
          opacity: 1;
          transform: scaleY(1);
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

        .kpi-card {
          transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
        }
        .kpi-card:hover {
          transform: translateY(-4px) scale(1.015);
          box-shadow:
            0 0 0 1px rgba(0, 230, 195, 0.35),
            0 16px 40px rgba(0, 0, 0, 0.5),
            0 0 30px rgba(0, 230, 195, 0.14);
          border-color: rgba(0, 230, 195, 0.45) !important;
        }

        .activity-row {
          position: relative;
          transition: background 0.2s;
        }
        .activity-row::after {
          content: "";
          position: absolute;
          inset: 0;
          background: linear-gradient(90deg, transparent, rgba(0, 230, 195, 0.06), transparent);
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
      `}</style>
    </>
  );
}