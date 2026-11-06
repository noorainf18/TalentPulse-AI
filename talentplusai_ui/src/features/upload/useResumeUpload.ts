"use client";

import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

import { uploadResume } from "@/lib/api";

export function useResumeUpload() {
  return useMutation({
    mutationFn: uploadResume,
    onSuccess: (data) => {
      if (data.kind === "duplicate") {
        toast.info("Candidate already exists.");
      }
    },
    onError: (err) => {
      toast.error((err as Error).message || "Upload failed");
    },
  });
}
