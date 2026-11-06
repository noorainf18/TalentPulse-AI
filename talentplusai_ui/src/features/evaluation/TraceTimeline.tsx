import { Fragment } from "react";

import { aosFadeStagger } from "@/lib/aos";
import type { TraceStep } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function TraceTimeline({
  steps,
  showHeading = true,
}: {
  steps: TraceStep[];
  showHeading?: boolean;
}) {
  return (
    <section className="rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-5 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md">
      {showHeading ? <h3 className="mb-4 text-xl font-semibold text-white">Execution trace</h3> : null}
      {!steps.length && <p className={`text-base text-slate-300 ${aosFadeStagger(1)}`}>No trace events yet.</p>}

      {/* Mobile: vertical pipeline */}
      <div className="relative md:hidden">
        <div className="pointer-events-none absolute bottom-3 left-[19px] top-3 w-px bg-gradient-to-b from-[#00e6c8]/70 via-[#00e6c8]/28 to-transparent" aria-hidden />
        <div className="space-y-6">
          {steps.map((s, idx) => (
            <div key={`${s.step}-${idx}`} className={cn("relative flex gap-4", aosFadeStagger(idx))}>
              <div className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 border-[rgba(0,230,195,0.45)] bg-[rgba(13,30,46,0.96)] text-sm font-bold text-[#9fffe6] shadow-[0_0_18px_rgba(0,230,195,0.28)]">
                {idx + 1}
              </div>
              <div className="min-w-0 flex-1 rounded-xl border border-[rgba(0,230,200,0.15)] bg-gradient-to-br from-white/[0.07] to-transparent p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-base font-semibold text-white">{s.step}</span>
                  <span className="rounded-full border border-[rgba(0,230,195,0.35)] bg-[rgba(0,230,200,0.1)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[#9fffe6]">
                    {s.status}
                  </span>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-slate-300">{s.message}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Desktop: horizontal graph with connectors */}
      <div className="-mx-1 hidden overflow-x-auto pb-2 pt-1 md:block [scrollbar-color:rgba(0,230,195,0.35)_transparent] [scrollbar-width:thin]">
        <div className="flex min-w-min flex-nowrap items-start justify-center gap-0 px-1">
          {steps.map((s, idx) => (
            <Fragment key={`${s.step}-${idx}`}>
              <div
                className={cn(
                  "flex w-[min(22vw,200px)] min-w-[148px] shrink-0 flex-col items-center px-1",
                  aosFadeStagger(idx),
                )}
              >
                <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl border-2 border-[rgba(0,230,195,0.42)] bg-gradient-to-br from-[rgba(0,230,200,0.18)] to-[rgba(13,30,46,0.92)] text-lg font-bold text-white shadow-[0_0_28px_rgba(0,230,195,0.22)]">
                  {idx + 1}
                </div>
                <p className="mt-3 text-center text-sm font-semibold text-white">{s.step}</p>
                <span className="mt-1.5 rounded-full border border-[rgba(0,230,195,0.35)] bg-[rgba(0,230,200,0.1)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[#9fffe6]">
                  {s.status}
                </span>
                <p className="mt-3 w-full text-center text-xs leading-relaxed text-slate-400">{s.message}</p>
              </div>
              {idx < steps.length - 1 ? (
                <div
                  className="mx-0.5 mt-8 hidden h-[3px] min-w-[20px] max-w-[56px] flex-1 shrink self-start md:block md:min-w-[32px]"
                  aria-hidden
                >
                  <div className="h-full w-full rounded-full bg-gradient-to-r from-[#00e6c8]/65 via-[#00e6c8]/25 to-[#00e6c8]/08 shadow-[0_0_12px_rgba(0,230,195,0.25)]" />
                </div>
              ) : null}
            </Fragment>
          ))}
        </div>
      </div>
    </section>
  );
}
