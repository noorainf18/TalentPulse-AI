import UploadCard from "@/features/upload/UploadCard";

export default function UploadPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6 py-2">
      <div className="rounded-2xl border border-[rgba(0,230,200,0.12)] bg-[#0d1e2e]/92 p-6 shadow-[0_10px_30px_rgba(0,0,0,0.35)] backdrop-blur-xl">
        <h1 className="text-3xl font-bold text-white">Ingestion</h1>
        <p className="mt-2 text-base text-slate-300">
          Upload a candidate resume (PDF) and trigger end-to-end screening: parsing, evidence research, scoring, and
          ranking.
        </p>
      </div>
      <UploadCard />
    </div>
  );
}
