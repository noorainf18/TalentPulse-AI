"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchDashboardSummary } from "@/lib/api";

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: fetchDashboardSummary,
    refetchInterval: 15000,
  });
}
