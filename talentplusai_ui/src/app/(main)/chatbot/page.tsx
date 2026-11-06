"use client";

import { Bot, MessageCircle, Search } from "lucide-react";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Fragment, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { TalentPlusLogo } from "@/components/brand/TalentPlusLogo";
import { ChatMessage, useRagChat } from "@/features/chatbot/useRagChat";

/* ─────────────────────────────────────────────────────────────────── */
/*  CONSTANTS                                                           */
/* ─────────────────────────────────────────────────────────────────── */

const SUGGESTED_PROMPTS = [
  "List top 5 candidates for backend/AI engineering with evidence.",
  "Compare Sahil Sasane and Gaurav Tripathi for production AI systems.",
  "Who has strongest LangGraph + FastAPI experience?",
  "Identify hidden gems with strong GitHub activity but low resume scores.",
  "Which candidates fill critical team gaps in ML infrastructure?",
];

function messageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/* ─────────────────────────────────────────────────────────────────── */
/*  HUMAN ASKING ICON — custom SVG                                      */
/* ─────────────────────────────────────────────────────────────────── */

function HumanAskingIcon({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 36 36"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* Head */}
      <circle cx="13" cy="10" r="5" fill="currentColor" opacity="0.9" />
      {/* Body */}
      <path
        d="M4 28c0-5 4-8 9-8s9 3 9 8"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
        opacity="0.9"
      />
      {/* Speech bubble */}
      <rect x="21" y="4" width="13" height="10" rx="3" fill="currentColor" opacity="0.85" />
      <path d="M23 14l-2 3 4-1" fill="currentColor" opacity="0.85" />
      {/* Dots inside bubble */}
      <circle cx="25" cy="9" r="1.2" fill="white" opacity="0.9" />
      <circle cx="28" cy="9" r="1.2" fill="white" opacity="0.9" />
      <circle cx="31" cy="9" r="1.2" fill="white" opacity="0.9" />
    </svg>
  );
}

/* ─────────────────────────────────────────────────────────────────── */
/*  MARKDOWN RENDERER                                                   */
/* ─────────────────────────────────────────────────────────────────── */

function renderInline(text: string): ReactNode {
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={index} className="font-semibold text-cyan-200">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <Fragment key={index}>{part}</Fragment>;
  });
}

function renderStructuredText(content: string): ReactNode {
  const lines = content.split("\n");
  const nodes: ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i].trim();
    if (!line) { i++; continue; }

    if (line.startsWith("### ")) {
      nodes.push(<h3 key={`h3-${i}`} className="mt-4 text-base font-semibold text-cyan-100">{renderInline(line.slice(4))}</h3>);
      i++; continue;
    }
    if (line.startsWith("## ")) {
      nodes.push(<h2 key={`h2-${i}`} className="mt-5 text-lg font-bold text-white">{renderInline(line.slice(3))}</h2>);
      i++; continue;
    }
    if (line.startsWith("# ")) {
      nodes.push(<h1 key={`h1-${i}`} className="mt-5 text-xl font-bold text-white">{renderInline(line.slice(2))}</h1>);
      i++; continue;
    }

    if (/^[-*]\s+/.test(line)) {
      const items: ReactNode[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        const text = lines[i].trim().replace(/^[-*]\s+/, "");
        items.push(<li key={`li-${i}`} className="text-sm leading-7 text-slate-200">{renderInline(text)}</li>);
        i++;
      }
      nodes.push(<ul key={`ul-${i}`} className="mt-2 list-disc space-y-1 pl-5">{items}</ul>);
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      const items: ReactNode[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        const text = lines[i].trim().replace(/^\d+\.\s+/, "");
        items.push(<li key={`ol-li-${i}`} className="text-sm leading-7 text-slate-200">{renderInline(text)}</li>);
        i++;
      }
      nodes.push(<ol key={`ol-${i}`} className="mt-2 list-decimal space-y-1 pl-5">{items}</ol>);
      continue;
    }

    if (line.startsWith("|")) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) { tableLines.push(lines[i].trim()); i++; }
      const normalized = tableLines
        .map((row) => row.replace(/^\||\|$/g, "").split("|").map((c) => c.trim()))
        .filter((row) => row.some((c) => c.length > 0));
      const sepIdx = normalized.findIndex((row) => row.every((c) => /^:?-{2,}:?$/.test(c)));
      const header = sepIdx > 0 ? normalized[sepIdx - 1] : normalized[0];
      const bodyRows = sepIdx >= 0 ? normalized.slice(sepIdx + 1) : normalized.slice(1);
      nodes.push(
        <div key={`table-${i}`} className="mt-3 overflow-x-auto rounded-xl border border-cyan-400/12 bg-[#0d1e2e]/92 backdrop-blur-xl">
          <table className="min-w-full text-left text-xs leading-6 text-slate-200">
            <thead className="border-b border-cyan-400/10 bg-[#112234]/55 text-xs uppercase tracking-wider text-slate-400">
              <tr>{header.map((c, idx) => <th key={idx} className="px-3 py-2 font-semibold">{renderInline(c)}</th>)}</tr>
            </thead>
            <tbody>
              {bodyRows.map((row, ri) => (
                <tr key={ri} className="border-b border-cyan-400/[0.08] last:border-b-0 hover:bg-cyan-400/[0.04]">
                  {header.map((_, ci) => <td key={ci} className="px-3 py-2 text-slate-200">{renderInline(row[ci] ?? "")}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    nodes.push(<p key={`p-${i}`} className="mt-2 text-sm leading-7 text-slate-200">{renderInline(line)}</p>);
    i++;
  }
  return <div>{nodes}</div>;
}

/* ─────────────────────────────────────────────────────────────────── */
/*  PARTICLE NETWORK BACKGROUND                                         */
/* ─────────────────────────────────────────────────────────────────── */

function ParticleNetwork() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const cnv = canvas;
    const c = ctx;

    const NODE_COUNT = 80;
    const MAX_DIST = 160;
    const TEAL = "0,230,200";
    const INDIGO = "129,140,248";

    type Particle = {
      x: number;
      y: number;
      vx: number;
      vy: number;
      r: number;
      color: string;
      opacity: number;
    };

    let W = 0;
    let H = 0;
    let mouseX = -999;
    let mouseY = -999;
    const particles: Particle[] = [];

    function seed() {
      particles.length = 0;
      for (let i = 0; i < NODE_COUNT; i++) {
        particles.push({
          x: Math.random() * W,
          y: Math.random() * H,
          vx: (Math.random() - 0.5) * 0.35,
          vy: (Math.random() - 0.5) * 0.35,
          r: Math.random() * 1.8 + 0.6,
          color: Math.random() > 0.6 ? INDIGO : TEAL,
          opacity: Math.random() * 0.5 + 0.3,
        });
      }
    }

    function resize() {
      W = window.innerWidth;
      H = window.innerHeight;
      cnv.width = W;
      cnv.height = H;
      seed();
    }

    function onMouseMove(e: MouseEvent) {
      mouseX = e.clientX;
      mouseY = e.clientY;
    }

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("mousemove", onMouseMove);

    function draw() {
      c.fillStyle = "#060d14";
      c.fillRect(0, 0, W, H);

      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = W;
        if (p.x > W) p.x = 0;
        if (p.y < 0) p.y = H;
        if (p.y > H) p.y = 0;

        const dx = mouseX - p.x;
        const dy = mouseY - p.y;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d < 200 && d > 0) {
          p.vx += (dx / d) * 0.008;
          p.vy += (dy / d) * 0.008;
        }
        const sp = Math.sqrt(p.vx * p.vx + p.vy * p.vy);
        if (sp > 0.9) {
          p.vx *= 0.95;
          p.vy *= 0.95;
        }
      }

      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i];
          const b = particles[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < MAX_DIST) {
            const alpha = (1 - dist / MAX_DIST) * 0.3;
            c.beginPath();
            c.moveTo(a.x, a.y);
            c.lineTo(b.x, b.y);
            c.strokeStyle = `rgba(${a.color},${alpha})`;
            c.lineWidth = 0.7;
            c.stroke();
          }
        }
      }

      for (const p of particles) {
        c.beginPath();
        c.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        c.fillStyle = `rgba(${p.color},${p.opacity})`;
        c.fill();
      }

      animRef.current = requestAnimationFrame(draw);
    }

    draw();
    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", onMouseMove);
    };
  }, []);

  return <canvas ref={canvasRef} aria-hidden className="pointer-events-none fixed inset-0 z-0" />;
}

/* ─────────────────────────────────────────────────────────────────── */
/*  RIPPLE HOOK                                                          */
/* ─────────────────────────────────────────────────────────────────── */

function useRipple() {
  const [ripples, setRipples] = useState<{ id: number; x: number; y: number }[]>([]);

  const addRipple = (e: React.MouseEvent<HTMLButtonElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const id = Date.now();
    setRipples((r) => [...r, { id, x: e.clientX - rect.left, y: e.clientY - rect.top }]);
    setTimeout(() => setRipples((r) => r.filter((rp) => rp.id !== id)), 700);
  };

  return { ripples, addRipple };
}

/* ─────────────────────────────────────────────────────────────────── */
/*  MAIN PAGE                                                            */
/* ─────────────────────────────────────────────────────────────────── */

export default function ChatBotPage() {
  const [question, setQuestion] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [topK, setTopK] = useState(10);
  const [focused, setFocused] = useState(false);
  const ragAsk = useRagChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { ripples, addRipple } = useRipple();
  const promptsRef = useRef<HTMLDivElement>(null);

  /**
   * FIX: Read candidate_id from the URL query string.
   *
   * The chatbot can be opened in two modes:
   *   1. Global mode  — /chatbot              (no candidate_id param)
   *      Searches across all indexed candidates. Good for shortlisting queries.
   *   2. Scoped mode  — /chatbot?candidate_id=<uuid>
   *      All retrieval is filtered to this one candidate. Use this when opening
   *      the chat from a specific candidate's evidence panel so answers are
   *      always grounded in that candidate's resume and nothing else.
   *
   * To open the chat in scoped mode from elsewhere in the app, navigate to:
   *   /chatbot?candidate_id=<the-candidate-uuid>
   */
  const searchParams = useSearchParams();
  const candidateId = searchParams.get("candidate_id") ?? undefined;

  const canAsk = question.trim().length > 2 && !ragAsk.isPending;
  const welcomeVisible = useMemo(() => messages.length === 0, [messages.length]);

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, ragAsk.isPending]);

  // Prompt slider auto-scroll
  useEffect(() => {
    const el = promptsRef.current;
    if (!el) return;
    let scrollDir = 1;
    const interval = setInterval(() => {
      el.scrollLeft += scrollDir * 1.2;
      if (el.scrollLeft + el.clientWidth >= el.scrollWidth - 2) scrollDir = -1;
      if (el.scrollLeft <= 0) scrollDir = 1;
    }, 20);
    return () => clearInterval(interval);
  }, []);

  // FIX: Reset session when candidateId changes (e.g. user navigates from one
  // candidate's chat to another's). Keeping the old session_id would cause the
  // backend to inherit the previous candidate's context.
  useEffect(() => {
    setMessages([]);
    setSessionId(undefined);
  }, [candidateId]);

  async function onAsk(e: FormEvent) {
    e.preventDefault();
    const clean = question.trim();
    if (!clean) return;

    setMessages((prev) => [...prev, { id: messageId(), role: "user", content: clean }]);
    setQuestion("");

    try {
      /**
       * FIX: Pass candidate_id in every ask payload.
       * Previously this was omitted entirely, so the backend serializer
       * never received it and retrieval always searched all candidates.
       */
      const response = await ragAsk.mutateAsync({
        question: clean,
        session_id: sessionId,
        top_k: topK,
        ...(candidateId ? { candidate_id: candidateId } : {}),
      });
      setSessionId(response.session_id);
      setMessages((prev) => [
        ...prev,
        { id: messageId(), role: "assistant", content: response.answer, citations: response.citations },
      ]);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to fetch answer.";
      toast.error(message);
      setMessages((prev) => [
        ...prev,
        { id: messageId(), role: "assistant", content: "I could not process that request right now. Please retry." },
      ]);
    }
  }

  return (
    <>
      <ParticleNetwork />

      {/* Keyframes */}
      <style>{`
        @keyframes orb-pulse {
          0%, 100% { box-shadow: 0 0 20px 4px rgba(34,211,238,0.18), 0 0 40px 12px rgba(20,184,166,0.08); }
          50% { box-shadow: 0 0 28px 8px rgba(34,211,238,0.28), 0 0 56px 18px rgba(20,184,166,0.12); }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-8px); }
        }
        @keyframes ripple-anim {
          to { transform: scale(4); opacity: 0; }
        }
        @keyframes msg-in {
          from { opacity: 0; transform: translateY(14px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes thinking-dot {
          0%, 80%, 100% { transform: scale(0.7); opacity: 0.4; }
          40% { transform: scale(1); opacity: 1; }
        }
        @keyframes border-shimmer {
          0% { background-position: 0% 50%; }
          100% { background-position: 200% 50%; }
        }
        .msg-in { animation: msg-in 0.35s cubic-bezier(0.22,1,0.36,1) both; }
        .orb-float { animation: float 4s ease-in-out infinite; }
        .orb-glow { animation: orb-pulse 3s ease-in-out infinite; }
        .prompt-chip:hover { transform: translateY(-3px) scale(1.03); box-shadow: 0 8px 24px rgba(34,211,238,0.25); }
        .ask-btn:hover:not(:disabled) { transform: scale(1.03); box-shadow: 0 12px 32px rgba(34,211,238,0.45); }
        .ask-btn:active:not(:disabled) { transform: scale(0.97); }
        .glass-card { backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px); }
        .input-glow:focus { box-shadow: 0 0 0 2px rgba(34,211,238,0.35), 0 0 24px rgba(34,211,238,0.15); }
        .shimmer-border {
          background: linear-gradient(90deg, transparent, rgba(34,211,238,0.4), rgba(99,102,241,0.4), transparent);
          background-size: 200% 100%;
          animation: border-shimmer 2s linear infinite;
        }
        .thinking-dot { animation: thinking-dot 1.2s ease-in-out infinite; }
        .thinking-dot:nth-child(2) { animation-delay: 0.2s; }
        .thinking-dot:nth-child(3) { animation-delay: 0.4s; }
      `}</style>

      <div className="relative z-10 mx-auto flex min-h-[calc(100vh-3.5rem)] w-full max-w-4xl flex-col px-4 py-6">
        <div className="relative mb-4 w-full shrink-0">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-full border border-[rgba(0,230,200,0.18)] bg-[#0d1e2e]/40 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] text-cyan-200/90 backdrop-blur-sm transition hover:border-cyan-300/40 hover:bg-cyan-400/10 hover:text-cyan-100"
          >
            Back
          </Link>
        </div>

        {/* ── HERO ── */}
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="orb-float orb-glow mb-6 rounded-[18px]">
            <TalentPlusLogo
              variant="mark"
              className="h-24 w-24 overflow-hidden rounded-[18px] shadow-[0_0_28px_rgba(34,211,238,0.22)]"
            />
          </div>

          <h1
            className="mb-3 text-5xl font-black tracking-tight text-white"
            style={{ fontFamily: "'Syne', 'Rajdhani', sans-serif", letterSpacing: "-0.02em" }}
          >
            TalentPlus{" "}
            <span className="text-transparent" style={{ WebkitTextStroke: "1.5px rgba(34,211,238,0.8)" }}>
              GPT
            </span>
          </h1>
          <p className="max-w-md text-base text-[#e2f0f8]/72">
            Ask anything about your candidate pool — evidence-grounded, session-aware hiring intelligence.
          </p>

          {/* FIX: Show a scoped-mode badge when a candidate_id is active so the
              recruiter knows the chat is locked to a single candidate. */}
          {candidateId ? (
            <span className="mt-3 rounded-full border border-amber-300/35 bg-amber-400/10 px-3 py-1 text-xs text-amber-200">
              Scoped to candidate · {candidateId.slice(0, 12)}…
            </span>
          ) : sessionId ? (
            <span className="mt-3 rounded-full border border-cyan-300/25 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-200">
              Session: {sessionId.slice(0, 12)}…
            </span>
          ) : null}

          {/* Pills row */}
          <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-xs text-slate-300">
            <span className="flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 glass-card">
              <Bot className="h-3.5 w-3.5 text-cyan-300" /> Session aware
            </span>
            <span className="flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 glass-card">
              <Search className="h-3.5 w-3.5 text-cyan-300" /> Resume grounded
            </span>
            <span className="flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 glass-card">
              <MessageCircle className="h-3.5 w-3.5 text-violet-300" /> RAG powered
            </span>
          </div>
        </div>

        {/* ── SEARCH-STYLE INPUT (ShikshaGPT style) ── */}
        <form
          onSubmit={onAsk}
          className={`relative mb-6 transition-all duration-300 ${focused ? "scale-[1.015]" : ""}`}
        >
          <div
              className={`flex items-center rounded-full border bg-[#0d1e2e]/90 glass-card transition-all duration-300 ${
              focused
                ? "border-cyan-300/60 shadow-[0_0_0_4px_rgba(34,211,238,0.12),0_0_32px_rgba(34,211,238,0.18)]"
                : "border-white/20"
            }`}
          >
            {/* Left icon */}
            <div className="flex h-12 w-14 items-center justify-center pl-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-full border border-cyan-300/40 bg-cyan-400/15">
                <HumanAskingIcon className="h-5 w-5 text-cyan-300" />
              </div>
            </div>

            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              placeholder={
                candidateId
                  ? "Ask anything about this candidate…"
                  : "Write your query on candidates here…"
              }
              className="h-14 flex-1 bg-transparent text-sm text-slate-100 placeholder:text-slate-400 outline-none"
            />

            {/* top_k inline */}
            <div className="mr-2 hidden items-center gap-1.5 text-xs text-slate-400 sm:flex">
              top_k
              <input
                type="number"
                min={3}
                max={20}
                value={topK}
                onChange={(e) => setTopK(Math.max(3, Math.min(20, Number(e.target.value) || 10)))}
                className="w-14 rounded-md border border-cyan-300/25 bg-[#112234] px-2 py-1 text-center text-[#e2f0f8] outline-none"
              />
            </div>

            {/* Ask button */}
            <button
              type="submit"
              disabled={!canAsk}
              onClick={addRipple}
              className="ask-btn relative mr-2 flex h-10 items-center overflow-hidden rounded-full bg-gradient-to-r from-cyan-400 to-teal-500 px-5 text-sm font-bold text-slate-950 transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {ripples.map((rp) => (
                <span
                  key={rp.id}
                  className="pointer-events-none absolute rounded-full bg-white/40"
                  style={{
                    left: rp.x - 10,
                    top: rp.y - 10,
                    width: 20,
                    height: 20,
                    animation: "ripple-anim 0.7s ease-out forwards",
                  }}
                />
              ))}
              Ask
            </button>
          </div>
        </form>

        {/* ── SUGGESTED PROMPTS (auto-scrolling slider) ── */}
        <div className="relative mb-6">
          {/* Fade edges */}
          <div className="pointer-events-none absolute left-0 top-0 z-10 h-full w-12 bg-gradient-to-r from-[#060d14] to-transparent" />
          <div className="pointer-events-none absolute right-0 top-0 z-10 h-full w-12 bg-gradient-to-l from-[#060d14] to-transparent" />

          <div
            ref={promptsRef}
            className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide"
            style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
          >
            {SUGGESTED_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => setQuestion(prompt)}
                className="prompt-chip shrink-0 rounded-full border border-cyan-300/25 bg-white/5 px-4 py-2 text-sm text-slate-200 transition-all duration-200 hover:border-cyan-300/50 hover:bg-cyan-400/12 hover:text-white glass-card"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>

        {/* ── CONVERSATION ── */}
        <div className="flex-1 rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[#0d1e2e]/62 glass-card shadow-[0_16px_48px_rgba(2,6,23,0.4)]">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-white/10 px-5 py-3">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-cyan-200">
              <MessageCircle className="h-3.5 w-3.5" />
              Conversation
            </div>
            {messages.length > 0 && (
              <button
                type="button"
                onClick={() => { setMessages([]); setSessionId(undefined); }}
                className="rounded-lg px-2 py-1 text-xs text-slate-400 transition hover:bg-white/10 hover:text-white"
              >
                Clear
              </button>
            )}
          </div>

          {/* Messages */}
          <div className="max-h-[50vh] space-y-4 overflow-y-auto p-4 pr-3">
            {welcomeVisible ? (
              <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full border border-dashed border-cyan-300/30 bg-cyan-400/5">
                  <HumanAskingIcon className="h-9 w-9 text-cyan-300/60" />
                </div>
                <p className="text-sm text-slate-400">
                  {candidateId
                    ? "Ask anything about this candidate — answers are grounded in their resume only."
                    : "Ask to shortlist top-fit candidates fast."}
                </p>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <article
                  key={msg.id}
                  className={`msg-in rounded-2xl border p-4 transition-all duration-200 ${
                    msg.role === "user"
                      ? "ml-auto max-w-[88%] border-cyan-300/25 bg-gradient-to-br from-cyan-500/15 to-blue-500/10 hover:border-cyan-300/45"
                      : "mr-auto max-w-[96%] border-white/12 bg-white/5 hover:border-white/22"
                  }`}
                  style={{ animationDelay: `${idx * 0.04}s` }}
                >
                  <div className="mb-2.5 flex items-center gap-2">
                    {msg.role === "user" ? (
                      <span className="relative flex h-9 w-9 items-center justify-center rounded-full border border-cyan-300/40 bg-cyan-400/15 text-cyan-200">
                        <HumanAskingIcon className="h-5 w-5" />
                        <span className="absolute -bottom-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-cyan-400 text-[8px] font-black text-slate-950">?</span>
                      </span>
                    ) : (
                      <span className="flex h-9 w-9 items-center justify-center rounded-full border border-violet-300/35 bg-violet-400/15 text-violet-200">
                        <Bot className="h-4 w-4" />
                      </span>
                    )}
                    <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                      {msg.role === "user" ? "You" : "TalentPlus AI"}
                    </p>
                  </div>

                  <div className="text-sm">
                    {msg.role === "assistant"
                      ? renderStructuredText(msg.content)
                      : <p className="text-sm leading-7 text-slate-100">{msg.content}</p>}
                  </div>

                  {!!msg.citations?.length && (
                    <div className="mt-3 flex flex-wrap gap-2 border-t border-white/10 pt-3">
                      {msg.citations.slice(0, 6).map((c) => (
                        <span
                          key={`${c.candidate_id}-${c.chunk_index}`}
                          className="rounded-full border border-cyan-300/20 bg-cyan-400/8 px-2.5 py-1 text-xs text-cyan-300 transition hover:border-cyan-300/40 hover:bg-cyan-400/15"
                        >
                          #{c.rank} · {c.candidate_id.slice(0, 8)} · {c.score}
                        </span>
                      ))}
                    </div>
                  )}
                </article>
              ))
            )}

            {/* Thinking indicator */}
            {ragAsk.isPending && (
              <div className="msg-in mr-auto flex max-w-xs items-center gap-3 rounded-2xl border border-cyan-300/20 bg-cyan-400/8 px-4 py-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-full border border-violet-300/30 bg-violet-400/12">
                  <Bot className="h-3.5 w-3.5 text-violet-300" />
                </span>
                <span className="flex items-center gap-1.5 text-xs text-cyan-200">
                  Thinking
                  <span className="thinking-dot inline-block h-1.5 w-1.5 rounded-full bg-cyan-300" />
                  <span className="thinking-dot inline-block h-1.5 w-1.5 rounded-full bg-cyan-300" />
                  <span className="thinking-dot inline-block h-1.5 w-1.5 rounded-full bg-cyan-300" />
                </span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Bottom spacer */}
        <div className="h-4" />
      </div>
    </>
  );
}