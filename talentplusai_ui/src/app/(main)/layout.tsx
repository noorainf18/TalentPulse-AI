"use client";

import { usePathname, useRouter } from "next/navigation";
import { Suspense, useEffect } from "react";

import AppShell from "@/components/shell/AppShell";
import { useSession } from "@/features/auth/useSession";

export default function MainAppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { data, isLoading, isError } = useSession();

  useEffect(() => {
    if (isLoading) return;
    if (isError || !data) {
      const next = encodeURIComponent(pathname || "/dashboard");
      router.replace(`/login?next=${next}`);
    }
  }, [isLoading, isError, data, router, pathname]);

  if (isLoading || isError || !data) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#060d14] text-[#e2f0f8]/85">
        <div className="text-center text-base">Checking session…</div>
      </div>
    );
  }

  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-[#060d14] text-[#e2f0f8]/85">
          <div className="text-center text-base">Loading workspace…</div>
        </div>
      }
    >
      <AppShell>{children}</AppShell>
    </Suspense>
  );
}
