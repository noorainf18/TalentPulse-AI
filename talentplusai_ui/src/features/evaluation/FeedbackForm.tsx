"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { submitFeedback } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function FeedbackForm({
  candidateId,
  initialThumbsUp = null,
  initialNotes = "",
  sectionClassName,
}: {
  candidateId: string;
  initialThumbsUp?: boolean | null;
  initialNotes?: string;
  /** Optional AOS / layout classes for the outer section */
  sectionClassName?: string;
}) {
  const [thumbsUp, setThumbsUp] = useState<boolean | null>(initialThumbsUp ?? null);
  const [notes, setNotes] = useState(initialNotes);
  const queryClient = useQueryClient();

  useEffect(() => {
    setThumbsUp(initialThumbsUp ?? null);
    setNotes(initialNotes ?? "");
  }, [candidateId, initialThumbsUp, initialNotes]);

  const mutation = useMutation({
    mutationFn: () => {
      if (thumbsUp === null) throw new Error("Select thumbs up/down");
      return submitFeedback({ candidate_id: candidateId, thumbs_up: thumbsUp, notes });
    },
    onSuccess: () => {
      toast.success("Feedback saved");
      queryClient.invalidateQueries({ queryKey: ["evaluation", candidateId] });
    },
    onError: (err) => toast.error((err as Error).message),
  });

  return (
    <section
      className={cn(
        "rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[rgba(13,30,46,0.88)] p-5 shadow-[0_10px_30px_rgba(2,6,23,0.4)] backdrop-blur-md",
        sectionClassName,
      )}
    >
      <h3 className="mb-3 text-xl font-semibold text-white">Recruiter feedback</h3>
      <div className="mb-3 flex gap-2">
        <button
          type="button"
          onClick={() => setThumbsUp(true)}
          className={`rounded-lg px-3 py-2 text-base font-medium ${
            thumbsUp === true ? "bg-emerald-500 text-white" : "bg-white/10 text-slate-100 hover:bg-white/20"
          }`}
        >
          Thumbs up
        </button>
        <button
          type="button"
          onClick={() => setThumbsUp(false)}
          className={`rounded-lg px-3 py-2 text-base font-medium ${
            thumbsUp === false ? "bg-rose-500 text-white" : "bg-white/10 text-slate-100 hover:bg-white/20"
          }`}
        >
          Thumbs down
        </button>
      </div>
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Optional notes"
        className="mb-3 min-h-24 w-full rounded-lg border border-[rgba(0,230,200,0.22)] bg-[#0a1624]/90 p-3 text-base text-white outline-none ring-[rgba(0,230,195,0.35)] focus:ring-2"
      />
      <button
        type="button"
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="rounded-lg border border-[rgba(0,230,195,0.45)] bg-gradient-to-r from-[#00e6c3] to-[#00ffc8] px-4 py-2 text-base font-semibold text-slate-950 shadow-[0_0_14px_rgba(0,230,195,0.28)] hover:brightness-110 hover:shadow-[0_0_22px_rgba(0,255,200,0.45)] disabled:opacity-50"
      >
        {mutation.isPending ? "Saving…" : "Save feedback"}
      </button>
    </section>
  );
}
