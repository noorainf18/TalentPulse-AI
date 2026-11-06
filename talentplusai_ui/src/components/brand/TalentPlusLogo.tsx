"use client";

import Image from "next/image";
import { useId } from "react";

import { cn } from "@/lib/utils";

type Props = { className?: string; variant?: "full" | "mark" };

/**
 * Original T+ mark: gradient tile with white T stem + crossbar and + glyph.
 */
function LogoMark({ className = "" }: { className?: string }) {
  const gid = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  return (
    <svg
      viewBox="0 0 80 80"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("shrink-0", className)}
      aria-hidden
    >
      <defs>
        <linearGradient id={`${gid}-tile`} x1="12" y1="12" x2="68" y2="68" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#14b8a6" />
          <stop offset="100%" stopColor="#0d9488" />
        </linearGradient>
      </defs>
      <rect width="80" height="80" rx="18" fill={`url(#${gid}-tile)`} />
      <rect x="22" y="24" width="22" height="7" rx="1.5" fill="white" />
      <rect x="29.5" y="24" width="7" height="34" rx="1.5" fill="white" />
      <rect x="50" y="38" width="14" height="5" rx="1" fill="white" fillOpacity={0.95} />
      <rect x="54.5" y="33.5" width="5" height="14" rx="1" fill="white" fillOpacity={0.95} />
    </svg>
  );
}

/**
 * Uses brand assets in /public/brand for full wordmark.
 * Mark is the original T+ tile (gradient + white letterforms).
 */
export function TalentPlusLogo({ className = "", variant = "full" }: Props) {
  if (variant === "mark") {
    return <LogoMark className={cn("h-9 w-9", className)} />;
  }

  return (
    <div className={`flex items-center ${className}`}>
      <Image
        src="/brand/talentplus-logo-full.png"
        alt="TalentPlus AI"
        width={260}
        height={62}
        className="h-11 w-auto max-w-[min(100%,260px)] object-contain object-left"
        priority
      />
    </div>
  );
}
