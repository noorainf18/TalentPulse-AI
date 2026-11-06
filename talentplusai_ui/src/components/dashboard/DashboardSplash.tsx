"use client";

import { LoginWatermark } from "@/components/login/LoginWatermark";

/**
 * Dashboard splash: use the same watermark as login page.
 * Intentionally no centered icon/wordmark.
 */
export function DashboardSplash() {
  return (
    <div className="relative h-full min-h-[calc(100vh-3.5rem-3rem)] w-full overflow-hidden bg-[#F8FAFC]">
      <LoginWatermark />
    </div>
  );
}
