"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useResumeUpload } from "./useResumeUpload";

const STAGES = [
  "Uploading PDF",
  "Parsing with Docling",
  "Extracting structured data",
  "Saving candidate",
  "Queuing screening pipeline",
];

export default function UploadCard() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [stageIndex, setStageIndex] = useState(0);
  const [showAnalyzer, setShowAnalyzer] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const mutation = useResumeUpload();

  useEffect(() => {
    if (!mutation.isPending) return;
    const id = setInterval(() => setStageIndex((prev) => (prev + 1) % STAGES.length), 5000);
    return () => clearInterval(id);
  }, [mutation.isPending]);

  const disableSubmit = !file || mutation.isPending;
  const stage = useMemo(() => STAGES[stageIndex], [stageIndex]);
  const statusText = isSuccess ? "Resume extracted successfully." : "Extracting data using AI...";

  useEffect(() => {
    if (!mutation.isSuccess || !mutation.data) return;
    setIsSuccess(true);
    const timer = setTimeout(() => {
      router.push(`/candidates/${mutation.data?.candidate_id}`);
    }, 1200);
    return () => clearTimeout(timer);
  }, [mutation.isSuccess, mutation.data, router]);

  useEffect(() => {
    if (mutation.isError) {
      setShowAnalyzer(false);
      setIsSuccess(false);
    }
  }, [mutation.isError]);

  function startUpload() {
    if (!file) return;
    setShowAnalyzer(true);
    setIsSuccess(false);
    mutation.mutate(file);
  }

  return (
    <div className="space-y-5 rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[#0d1e2e]/92 p-6 shadow-[0_10px_30px_rgba(0,0,0,0.35)] backdrop-blur-xl">
      <h2 className="text-xl font-semibold text-white">Upload resume</h2>
      <p className="text-base text-slate-300">PDF only - parsed and queued for the screening pipeline.</p>

      {/* ── File input — cyan accent on the Choose File pill ── */}
      <input
        type="file"
        accept="application/pdf"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        className="block w-full cursor-pointer rounded-xl border border-[rgba(0,230,200,0.22)] bg-[#0a1620]/90 px-3 py-2.5 text-base text-white file:mr-3 file:rounded-lg file:border-0 file:bg-[#00e6c8] file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-slate-950 hover:bg-[#0d1f2e]"
      />

      {file && (
        <div className="text-sm text-slate-300">
          Selected: <span className="font-medium text-white">{file.name}</span>
        </div>
      )}

      {/* ── Stage indicator — cyan themed ── */}
      {mutation.isPending && (
        <div className="rounded-xl border border-[rgba(0,230,195,0.35)] bg-[rgba(0,230,200,0.08)] px-3 py-2 font-mono text-sm text-[#9fffe6]">
          {stage}…
        </div>
      )}

      {/* ── Upload button — cyan-to-teal gradient matching AppShell's Upload CV button ── */}
      <button
        type="button"
        disabled={disableSubmit}
        onClick={startUpload}
        className="rounded-xl bg-gradient-to-r from-cyan-400 to-teal-400 px-5 py-2.5 text-base font-bold text-slate-950 shadow-[0_0_20px_rgba(34,211,238,0.4)] transition-all duration-300 hover:scale-[1.04] hover:shadow-[0_0_35px_rgba(34,211,238,0.7)] active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {mutation.isPending ? "Processing…" : "Upload file"}
      </button>

      {/* ── Full-screen analyzer modal — all cyan/teal, matching image 1 ── */}
      {showAnalyzer && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4 backdrop-blur-sm">
          <style>{`
            @keyframes upload-doc-scan {
              0%   { top: -42%; opacity: 0.95; }
              50%  { opacity: 1; }
              100% { top: 108%; opacity: 0.95; }
            }
            .upload-doc-scan-beam {
              animation: upload-doc-scan 2.1s ease-in-out infinite alternate;
            }

            @keyframes upload-doc-edge-glow {
              0%, 100% { box-shadow: 0 0 0 1px rgba(0,230,195,0.35), 0 0 18px rgba(0,230,195,0.15); }
              50%       { box-shadow: 0 0 0 1px rgba(0,255,200,0.45), 0 0 28px rgba(0,230,195,0.28); }
            }
            .upload-doc-glow {
              animation: upload-doc-edge-glow 2.4s ease-in-out infinite;
            }
          `}</style>

          {/* Modal card — matches the dark teal background from image 1 */}
          <div className="relative w-full max-w-2xl rounded-2xl border border-[rgba(0,230,195,0.35)] bg-[#071218] p-8 pb-14 text-center shadow-[0_24px_64px_rgba(0,0,0,0.75),0_0_12px_rgba(0,230,195,0.2)]">

            {/* Document icon with cyan scan beam */}
            <div
              className={`relative mx-auto mb-6 h-28 w-20 overflow-hidden rounded-sm border border-[rgba(0,230,200,0.25)] bg-gradient-to-b from-[#071a22] to-[#040e14] p-2 ${
                isSuccess ? "" : "upload-doc-glow"
              }`}
            >
              <div className="relative z-10 h-full w-full">
                {/* Simulated document lines */}
                <div className="h-2 w-12 rounded bg-[rgba(0,230,200,0.2)]" />
                <div className="mt-2 space-y-1">
                  <div className="h-1.5 w-14 rounded bg-[rgba(0,230,200,0.15)]" />
                  <div className="h-1.5 w-10 rounded bg-[rgba(0,230,200,0.15)]" />
                  <div className="h-1.5 w-full rounded bg-[rgba(0,230,200,0.15)]" />
                  <div className="h-1.5 w-full rounded bg-[rgba(0,230,200,0.15)]" />
                  <div className="h-1.5 w-8 rounded bg-[rgba(0,230,200,0.15)]" />
                </div>
              </div>

              {/* Scan beam — cyan, matching image 1 */}
              {!isSuccess && (
                <div className="upload-doc-scan-beam pointer-events-none absolute left-0 right-0 z-20 h-[36%] rounded-sm">
                  <div
                    className="absolute inset-0 rounded-sm"
                    style={{
                      background:
                        "linear-gradient(to bottom, transparent 0%, rgba(0,230,200,0.10) 35%, rgba(0,230,195,0.65) 50%, rgba(0,255,200,0.85) 50.5%, rgba(0,230,195,0.65) 51%, rgba(0,230,200,0.10) 65%, transparent 100%)",
                      filter: "blur(0.5px)",
                    }}
                  />
                  {/* Bright horizontal scan line */}
                  <div
                    className="absolute left-1 right-1 top-1/2 z-30 h-[14%] max-h-[10px] -translate-y-1/2 rounded-sm opacity-90"
                    style={{
                      background:
                        "linear-gradient(to right, transparent, rgba(159,255,230,0.95) 45%, rgba(0,255,200,0.98) 50%, rgba(159,255,230,0.95) 55%, transparent)",
                    }}
                  />
                </div>
              )}
            </div>

            {/* Status heading — cyan to match image 1 */}
            <p className="text-3xl font-medium tracking-tight text-[#00e6c8]">{statusText}</p>

            <p className="mt-2 font-mono text-base text-[rgba(159,255,230,0.75)]">
              {isSuccess ? "Redirecting to candidate profile..." : stage}
            </p>

            {/* Spinner — bottom-left, cyan ring matching image 1 */}
            {!isSuccess && (
              <div className="absolute bottom-6 left-6">
                <span
                  className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-[rgba(0,230,200,0.2)] border-t-[#00ffc8] shadow-[0_0_12px_rgba(0,230,195,0.45)]"
                  aria-hidden
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}