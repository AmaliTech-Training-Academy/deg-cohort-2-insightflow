"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { uploadFile, getJobStatus } from "@/api/uploads";
import type { IngestionJob } from "@/types";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { FileDropzone } from "@/components/ui/FileDropzone";
import { AlertBanner } from "@/components/ui/AlertBanner";
import { StatusBadge } from "@/components/ui/StatusBadge";

export default function NewUploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => uploadFile(file!, "pos"),
    onSuccess: (job) => setJobId(job.id),
  });

  const { data: job } = useQuery({
    queryKey: ["job-status", jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 1500;
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || mutation.isPending) return;
    mutation.mutate();
  }

  function handleReset() {
    setJobId(null);
    setFile(null);
    mutation.reset();
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">New upload</h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
          Import POS transactions from a CSV export.
        </p>
      </div>

      <div className="max-w-2xl mx-auto space-y-5">
        {!jobId ? (
          <Card title="New Upload">
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Data source badge — CSV only */}
              <div>
                <p className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">
                  Data Source
                </p>
                <div className="flex items-center gap-2.5 rounded-md border border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700/50 px-3 py-2.5">
                  <CsvIcon />
                  <div>
                    <p className="text-sm font-medium text-gray-800 dark:text-slate-200">CSV File</p>
                    <p className="text-xs text-gray-500 dark:text-slate-400">Comma-separated values, UTF-8 encoded</p>
                  </div>
                </div>
              </div>

              {/* File dropzone */}
              <div>
                <p className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">File</p>
                <FileDropzone
                  onFile={setFile}
                  accept=".csv"
                  disabled={mutation.isPending}
                />
                {file && (
                  <div className="mt-2.5 flex items-center gap-2 rounded-md border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/40 px-3 py-2">
                    <FileIcon />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-800 dark:text-slate-200 truncate">{file.name}</p>
                      <p className="text-xs text-gray-500 dark:text-slate-400">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setFile(null)}
                      className="ml-auto text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 transition-colors shrink-0"
                      aria-label="Remove file"
                    >
                      <XIcon />
                    </button>
                  </div>
                )}
              </div>

              {mutation.isError && (
                <AlertBanner variant="error" message="Upload failed. Please try again." />
              )}

              <Button
                type="submit"
                disabled={!file}
                loading={mutation.isPending}
                size="lg"
                className="w-full"
              >
                {mutation.isPending ? "Uploading…" : "Start Upload"}
              </Button>
            </form>
          </Card>
        ) : (
          <JobStatusCard job={job} onNewUpload={handleReset} />
        )}

        {/* Tips */}
        {!jobId && (
          <Card>
            <div className="space-y-2.5">
              <p className="text-sm font-semibold text-gray-700 dark:text-slate-300">File requirements</p>
              <ul className="space-y-1.5 text-sm text-gray-500 dark:text-slate-400">
                {[
                  "CSV only — .csv extension required",
                  "Max file size: 50 MB",
                  "First row must be the header row",
                  "Date columns must use ISO 8601 (YYYY-MM-DD)",
                ].map((tip) => (
                  <li key={tip} className="flex items-start gap-2">
                    <span className="mt-0.5 shrink-0 text-green-500 dark:text-green-400"><CheckSmallIcon /></span>
                    {tip}
                  </li>
                ))}
              </ul>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

/* ─── Job status card ─────────────────────────────────────── */

function JobStatusCard({
  job,
  onNewUpload,
}: {
  job: IngestionJob | undefined;
  onNewUpload: () => void;
}) {
  if (!job) {
    return (
      <Card title="Upload Status">
        <div className="flex items-center gap-3 py-4">
          <span className="animate-spin text-green-600"><SpinnerIcon /></span>
          <p className="text-sm text-gray-600 dark:text-slate-400">Starting upload…</p>
        </div>
      </Card>
    );
  }

  const isDone = job.status === "completed" || job.status === "failed";
  const progress =
    job.recordsTotal && job.recordsProcessed != null
      ? Math.round((job.recordsProcessed / job.recordsTotal) * 100)
      : 0;

  return (
    <Card title="Upload Status">
      <div className="space-y-4">
        {/* File info */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="font-medium text-gray-900 dark:text-slate-100 truncate">{job.fileName}</p>
            <p className="text-sm text-gray-500 dark:text-slate-400 mt-0.5">CSV File</p>
          </div>
          <StatusBadge status={job.status} />
        </div>

        {/* Pending */}
        {job.status === "pending" && (
          <div className="flex items-center gap-2.5 rounded-md bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 px-3 py-2.5 text-sm text-yellow-800 dark:text-yellow-300">
            <span className="animate-spin shrink-0"><SpinnerIcon /></span>
            Your file is queued for processing…
          </div>
        )}

        {/* Processing */}
        {job.status === "processing" && (
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-gray-500 dark:text-slate-400">
              <span>Processing records</span>
              <span>{job.recordsProcessed?.toLocaleString()} / {job.recordsTotal?.toLocaleString()}</span>
            </div>
            <div className="h-2 w-full rounded-full bg-gray-100 dark:bg-slate-700 overflow-hidden">
              <div
                className="h-full bg-green-500 rounded-full transition-all duration-700"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-gray-400 dark:text-slate-500">{progress}% complete</p>
          </div>
        )}

        {/* Completed */}
        {job.status === "completed" && (
          <div className="flex items-center gap-2.5 rounded-md bg-green-50 dark:bg-green-950/40 border border-green-200 dark:border-green-800 px-3 py-2.5 text-sm text-green-800 dark:text-green-300">
            <span className="shrink-0"><CheckCircleIcon /></span>
            Successfully ingested <strong>{job.recordsProcessed?.toLocaleString()}</strong> records.
          </div>
        )}

        {/* Failed */}
        {job.status === "failed" && (
          <AlertBanner
            variant="error"
            message={job.errorMessage ?? "An unknown error occurred during ingestion."}
          />
        )}

        {/* Actions */}
        {isDone && (
          <div className="flex gap-3 pt-1 border-t border-gray-100 dark:border-slate-700">
            <Button variant="primary" size="sm" onClick={onNewUpload}>
              Upload another file
            </Button>
            <Link
              href="/uploads/history"
              className="inline-flex items-center justify-center rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
            >
              View history
            </Link>
          </div>
        )}
      </div>
    </Card>
  );
}

/* ─── Icons ───────────────────────────────────────────────── */

function CsvIcon() {
  return (
    <div className="w-8 h-8 rounded-md bg-green-100 dark:bg-green-900/40 flex items-center justify-center shrink-0">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-green-600 dark:text-green-400">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="8" y1="13" x2="16" y2="13" />
        <line x1="8" y1="17" x2="16" y2="17" />
      </svg>
    </div>
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

function XIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function CheckSmallIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

function CheckCircleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}
