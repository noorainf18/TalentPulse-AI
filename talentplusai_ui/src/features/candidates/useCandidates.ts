"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchCandidates } from "@/lib/api";

export function useCandidates(filters?: { status?: string; min_score?: number }) {
  return useQuery({
    queryKey: ["candidates", filters?.status ?? "", filters?.min_score ?? ""],
    queryFn: () => fetchCandidates(filters),
  });
}
