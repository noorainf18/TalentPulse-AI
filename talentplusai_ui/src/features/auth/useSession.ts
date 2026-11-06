"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchAuthMe } from "@/lib/api";

export function useSession() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: fetchAuthMe,
    retry: false,
    staleTime: 60_000,
  });
}
