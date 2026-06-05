"use client";

import { useState, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { uploadFile, getJobStatus } from "@/api/uploads";
import type { IngestionJob } from "@/types";
import { Button } from "@/components/ui/Button";
import { FileDropzone } from "@/components/ui/FileDropzone";
import { AlertBanner } from "@/components/ui/AlertBanner";
import { StatusBadge } from "@/components/ui/StatusBadge";

// ── Types ────────────────────────────────────────────────────────────────────

type StepNumber = 1 | 2 | 3 | 4 | 5;

const STEPS: { n: StepNumber; label: string }[] = [
  { n: 1, label: "Select" },
  { n: 2, label: "Preview" },
  { n: 3, label: "Upload" },
  { n: 4, label: "Process" },
  { n: 5, label: "Summary" },
];

const POS_COLUMNS = [
  "transaction_id", "date", "store_id", "cashier_id",
  "product_sku", "quantity", "unit_price", "discount_applied", "total",
];

interface CSVPreview {
  headers: string[];
  rows: string[][];
  missingColumns: string[];
}

// ── Helpers ──────────────────────────────────────────────────────────────────

async function parseCSVPreview(file: File): Promise<CSVPreview> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = (e.target?.result as string) ?? "";
      const lines = text.split(/\r?\n/).filter(Boolean);
      const headers = (lines[0] ?? "")
        .split(",")
        .map((h) => h.trim().replace(/^"|"$/g, "").toLowerCase());
      const rows = lines.slice(1, 6).map((line) =>
        line.split(",").map((cell) => cell.trim().replace(/^"|"$/g, ""))
      );
      const missingColumns = POS_COLUMNS.filter((col) => !headers.includes(col));
      resolve({ headers, rows, missingColumns });
    };
    reader.readAsText(file);
  });
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function NewUploadPage() {
  const [step, setStep] = useState<StepNumber>(1);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CSVPreview | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => uploadFile(file!, "pos"),
    onSuccess: (job) => {
      setJobId(job.id);
      setStep(4);
    },
  });

  const { data: job } = useQuery({
    queryKey: ["job-status", jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: Boolean(jobId) && step === 4,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "completed" || s === "failed" ? false : 1500;
    },
  });

  useEffect(() => {
    if (job?.status === "completed" || job?.status === "failed") {
      setStep(5);
    }
  }, [job?.status]);

  async function handleFileSelected(f: File) {
    setFile(f);
    const parsed = await parseCSVPreview(f);
    setPreview(parsed);
  }

  function goToPreview() {
    if (file && preview) setStep(2);
  }

  function goToUpload() {
    setStep(3);
    mutation.mutate();
  }

  function reset() {
    setStep(1);
    setFile(null);
    setPreview(null);
    setJobId(null);
    mutation.reset();
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-semibold tracking-tight text-gray-900 dark:text-slate-100">New upload</h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
          Import POS transactions from a CSV export.
        </p>
      </div>

      <div className="space-y-4">
        <StepBar current={step} />

        {step === 1 && (
          <StepSelect
            file={file}
            preview={preview}
            onFile={handleFileSelected}
            onNext={goToPreview}
          />
        )}

        {step === 2 && preview && (
          <StepPreview
            file={file!}
            preview={preview}
            onBack={() => setStep(1)}
            onNext={goToUpload}
          />
        )}

        {step === 3 && (
          <StepUpload
            isError={mutation.isError}
            onRetry={() => { mutation.reset(); mutation.mutate(); }}
          />
        )}

        {step === 4 && <StepProcess job={job} />}

        {step === 5 && <StepSummary job={job} onReset={reset} />}
      </div>
    </div>
  );
}

// ── StepBar ───────────────────────────────────────────────────────────────────

function StepBar({ current }: { current: StepNumber }) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-6 py-4">
      <ol className="flex items-center gap-0">
        {STEPS.map(({ n, label }, idx) => {
          const done = current > n;
          const active = current === n;
          return (
            <li key={n} className="flex items-center flex-1 last:flex-none">
              <div className="flex items-center gap-2 shrink-0">
                <span
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                    done
                      ? "bg-green-600 text-white"
                      : active
                      ? "bg-green-600 text-white"
                      : "bg-gray-100 dark:bg-slate-700 text-gray-400 dark:text-slate-500"
                  }`}
                >
                  {done ? <CheckTinyIcon /> : n}
                </span>
                <span
                  className={`text-sm font-medium ${
                    active
                      ? "text-gray-900 dark:text-slate-100"
                      : done
                      ? "text-gray-500 dark:text-slate-400"
                      : "text-gray-400 dark:text-slate-500"
                  }`}
                >
                  {label}
                </span>
              </div>
              {idx < STEPS.length - 1 && (
                <div className={`flex-1 mx-3 h-px transition-colors ${done ? "bg-green-500" : "bg-gray-200 dark:bg-slate-700"}`} />
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

// ── Step 1: Select ────────────────────────────────────────────────────────────

function StepSelect({
  file,
  preview,
  onFile,
  onNext,
}: {
  file: File | null;
  preview: CSVPreview | null;
  onFile: (f: File) => void;
  onNext: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6">
        <FileDropzone onFile={onFile} accept=".csv" />
        {file && (
          <div className="mt-4 flex items-center gap-3 rounded-md border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/40 px-4 py-2.5">
            <FileIcon />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-800 dark:text-slate-200 truncate">{file.name}</p>
              <p className="text-xs text-gray-500 dark:text-slate-400">{(file.size / 1024).toFixed(1)} KB</p>
            </div>
            {preview?.missingColumns.length === 0 && (
              <span className="text-green-600 dark:text-green-400 shrink-0"><CheckCircleIcon /></span>
            )}
          </div>
        )}
        {preview && preview.missingColumns.length > 0 && (
          <div className="mt-3">
            <AlertBanner
              variant="error"
              message={`Missing required columns: ${preview.missingColumns.join(", ")}`}
            />
          </div>
        )}
        <div className="mt-4 flex justify-end">
          <Button
            onClick={onNext}
            disabled={!file || (preview?.missingColumns.length ?? 1) > 0}
          >
            Next
          </Button>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6">
        <div className="flex items-center gap-2 mb-3">
          <InfoIcon />
          <p className="text-sm font-semibold text-gray-700 dark:text-slate-300">Expected format</p>
        </div>
        <p className="text-sm text-gray-500 dark:text-slate-400 mb-3">
          The file must include these columns, comma-separated, with a header row:
        </p>
        <div className="flex flex-wrap gap-2">
          {POS_COLUMNS.map((col) => (
            <code
              key={col}
              className="rounded-md border border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700 px-2.5 py-1 text-xs text-gray-700 dark:text-slate-300 font-mono"
            >
              {col}
            </code>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Step 2: Preview ───────────────────────────────────────────────────────────

function StepPreview({
  file,
  preview,
  onBack,
  onNext,
}: {
  file: File;
  preview: CSVPreview;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 space-y-4">
      <div>
        <p className="text-sm font-medium text-gray-700 dark:text-slate-300">
          Previewing <span className="font-semibold">{file.name}</span>
        </p>
        <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">First 5 rows shown</p>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-slate-700">
        <table className="min-w-full divide-y divide-gray-100 dark:divide-slate-700 text-xs">
          <thead className="bg-gray-50 dark:bg-slate-700/50">
            <tr>
              {preview.headers.map((h) => (
                <th
                  key={h}
                  className="px-4 py-2.5 text-left font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400 whitespace-nowrap"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-slate-700 bg-white dark:bg-slate-800">
            {preview.rows.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50 dark:hover:bg-slate-700/50">
                {row.map((cell, j) => (
                  <td key={j} className="px-4 py-2.5 text-gray-700 dark:text-slate-300 whitespace-nowrap">
                    {cell || <span className="text-gray-300 dark:text-slate-600">—</span>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-slate-700">
        <Button variant="ghost" onClick={onBack}>Back</Button>
        <Button onClick={onNext}>Upload file</Button>
      </div>
    </div>
  );
}

// ── Step 3: Upload ────────────────────────────────────────────────────────────

function StepUpload({ isError, onRetry }: { isError: boolean; onRetry: () => void }) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-6 py-16 flex flex-col items-center gap-3 text-center">
      {!isError ? (
        <>
          <span className="animate-spin text-green-600 mb-1"><SpinnerLargeIcon /></span>
          <p className="text-sm font-medium text-gray-900 dark:text-slate-100">Uploading your file…</p>
          <p className="text-xs text-gray-400 dark:text-slate-500">This usually takes a few seconds.</p>
        </>
      ) : (
        <div className="w-full max-w-sm space-y-4">
          <AlertBanner variant="error" message="Upload failed. Please check your connection and try again." />
          <Button variant="secondary" onClick={onRetry} className="w-full">Retry upload</Button>
        </div>
      )}
    </div>
  );
}

// ── Step 4: Process ───────────────────────────────────────────────────────────

function StepProcess({ job }: { job: IngestionJob | undefined }) {
  const progress =
    job?.recordsTotal && job.recordsProcessed != null
      ? Math.round((job.recordsProcessed / job.recordsTotal) * 100)
      : 0;

  return (
    <div className="rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-6 py-12">
      <div className="flex flex-col items-center gap-3 text-center mb-6">
        <span className="animate-spin text-green-600"><SpinnerLargeIcon /></span>
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-slate-100">Processing records…</p>
          <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">
            {job?.status === "pending" ? "Queued, starting soon" : "Validating and inserting rows"}
          </p>
        </div>
        {job && <StatusBadge status={job.status} />}
      </div>

      {job?.status === "processing" && job.recordsTotal && (
        <div className="max-w-sm mx-auto space-y-2">
          <div className="h-1.5 w-full rounded-full bg-gray-100 dark:bg-slate-700 overflow-hidden">
            <div
              className="h-full bg-green-500 rounded-full transition-all duration-700"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-gray-400 dark:text-slate-500 text-center tabular-nums">
            {job.recordsProcessed?.toLocaleString()} / {job.recordsTotal.toLocaleString()} rows — {progress}%
          </p>
        </div>
      )}
    </div>
  );
}

// ── Step 5: Summary ───────────────────────────────────────────────────────────

function StepSummary({
  job,
  onReset,
}: {
  job: IngestionJob | undefined;
  onReset: () => void;
}) {
  const success = job?.status === "completed";

  return (
    <div className="rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 space-y-5">
      <div className="flex items-center gap-3">
        {success ? (
          <span className="text-green-600 dark:text-green-400"><CheckCircleIcon /></span>
        ) : (
          <span className="text-red-500"><ErrorCircleIcon /></span>
        )}
        <div>
          <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
            {success ? "Ingestion complete" : "Ingestion failed"}
          </p>
          <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
            {job?.fileName}
          </p>
        </div>
        {job && <div className="ml-auto"><StatusBadge status={job.status} /></div>}
      </div>

      {success && job?.recordsProcessed != null && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <SummaryTile label="Inserted" value={job.recordsProcessed.toLocaleString()} color="green" />
          {job.recordsTotal != null && (
            <SummaryTile label="Total rows" value={job.recordsTotal.toLocaleString()} color="gray" />
          )}
          {(job.skippedRows ?? 0) > 0 && (
            <SummaryTile label="Already exists" value={(job.skippedRows ?? 0).toLocaleString()} color="gray" />
          )}
          {(job.rejectedRows ?? 0) > 0 && (
            <SummaryTile label="FK misses" value={(job.rejectedRows ?? 0).toLocaleString()} color="yellow" />
          )}
          {(job.errorRows ?? 0) > 0 && (
            <SummaryTile label="Format errors" value={(job.errorRows ?? 0).toLocaleString()} color="red" />
          )}
        </div>
      )}

      {!success && job?.errorMessage && (
        <AlertBanner variant="error" message={job.errorMessage} />
      )}

      <div className="flex items-center gap-3 pt-2 border-t border-gray-100 dark:border-slate-700">
        <Button onClick={onReset}>Upload another file</Button>
        <Link href="/uploads/history" className="text-sm font-medium text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 transition-colors">
          View history →
        </Link>
      </div>
    </div>
  );
}

function SummaryTile({ label, value, color }: { label: string; value: string; color: "green" | "gray" | "yellow" | "red" }) {
  const valueClass =
    color === "green" ? "text-green-600 dark:text-green-400"
    : color === "yellow" ? "text-yellow-600 dark:text-yellow-400"
    : color === "red" ? "text-red-600 dark:text-red-400"
    : "text-gray-900 dark:text-slate-100";
  return (
    <div className="rounded-lg border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-700/50 px-5 py-4">
      <p className={`text-3xl font-semibold tracking-tight tabular-nums leading-none ${valueClass}`}>{value}</p>
      <p className="text-xs text-gray-500 dark:text-slate-400 mt-1.5">{label}</p>
    </div>
  );
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function CheckTinyIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-green-600 dark:text-green-400 shrink-0">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

function InfoIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400 dark:text-slate-500 shrink-0">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function SpinnerLargeIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

function CheckCircleIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}

function ErrorCircleIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}
