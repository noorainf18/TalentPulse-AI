"use client";

import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

const IO_OPTS: IntersectionObserverInit = {
  threshold: 0.12,
  rootMargin: "0px 0px -40px 0px",
};

/**
 * Observes `.aos-fade-up` descendants and adds `.visible` when they enter the viewport.
 * MutationObserver rescans when children mount (e.g. React Query, hash tabs).
 */
export default function AosScope({ className, children }: { className?: string; children: React.ReactNode }) {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("visible");
        io.unobserve(entry.target);
      });
    }, IO_OPTS);

    let debounce: ReturnType<typeof setTimeout> | undefined;
    const scan = () => {
      root.querySelectorAll<HTMLElement>(".aos-fade-up:not(.visible)").forEach((el) => io.observe(el));
    };
    const scheduleScan = () => {
      if (debounce != null) clearTimeout(debounce);
      debounce = setTimeout(() => {
        debounce = undefined;
        scan();
      }, 50);
    };

    scan();
    const mo = new MutationObserver(scheduleScan);
    mo.observe(root, { childList: true, subtree: true });

    return () => {
      if (debounce != null) clearTimeout(debounce);
      mo.disconnect();
      io.disconnect();
    };
  }, []);

  return (
    <div ref={rootRef} className={cn(className)}>
      {children}
    </div>
  );
}
