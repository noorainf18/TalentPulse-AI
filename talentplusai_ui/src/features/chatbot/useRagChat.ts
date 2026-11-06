"use client";

import { useMutation } from "@tanstack/react-query";

import { askRagChat } from "@/lib/api";
import type { RagAskResponse } from "@/lib/types";

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  citations?: RagAskResponse["citations"];
}

export function useRagChat() {
  return useMutation({
    mutationFn: askRagChat,
  });
}

