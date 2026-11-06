"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchEvidencePanel } from "@/lib/api";

export function useEvaluationDetail(candidateId: string) {
  return useQuery({
    queryKey: ["evaluation", candidateId],
    queryFn: () => fetchEvidencePanel(candidateId),
    enabled: Boolean(candidateId),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 3000;
      return data.kind === "pending" ? 3000 : false;
    },
  });
}
