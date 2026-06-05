"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { getIngestionHistory } from "@/api/history";
import { triggerOnlineOrders } from "@/api/onlineOrders";
import { triggerFeedback } from "@/api/feedback";
import type { IngestionJob } from "@/types";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { AlertBanner } from "@/components/ui/AlertBanner";
import { Pagination } from "@/components/ui/Pagination";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";

const SOURCE_LABELS: Record<string, string> = {
  pos:           "POS",
  inventory:     "Inventory",
  online_orders: "Online Orders",
  feedback:      "Feedback",
};

function formatDate(iso: string) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

const PAGE_SIZE = 8;

export default function UploadHistoryPage() {
  const [page, setPage] = useState(1);
  const [selectedJob, setSelectedJob] = useState<IngestionJob | null>(null);
  const [triggerMsg, setTriggerMsg] = useState<{ variant: "success" | "error"; text: string } | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["ingestion-history", page],
    queryFn: () => getIngestionHistory(page),
  });

  const feedbackMutation = useMutation({
    mutationFn: triggerFeedback,
    onSuccess: () => {
      setTriggerMsg({ variant: "success", text: "Feedback sync started successfully." });
      queryClient.invalidateQueries({ queryKey: ["ingestion-history"] });
    },
    onError: () => {
      setTriggerMsg({ variant: "error", text: "Failed to trigger feedback ingestion. Please try again." });
    },
  });

  const ordersMutation = useMutation({
    mutationFn: triggerOnlineOrders,
    onSuccess: () => {
      setTriggerMsg({ variant: "success", text: "Online orders sync started successfully." });
      queryClient.invalidateQueries({ queryKey: ["ingestion-history"] });
    },
    onError: () => {
      setTriggerMsg({ variant: "error", text: "Failed to trigger online orders ingestion. Please try again." });
    },
  });

  const totalPages = data ? Math.ceil(data.count / PAGE_SIZE) : 1;

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Ingestion history</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            All ingestion jobs — click a row to see full details.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <Button
            variant="secondary"
            size="sm"
            loading={feedbackMutation.isPending}
            onClick={() => { setTriggerMsg(null); feedbackMutation.mutate(); }}
          >
            Sync Feedbacks
          </Button>
          <Button
            variant="secondary"
            size="sm"
            loading={ordersMutation.isPending}
            onClick={() => { setTriggerMsg(null); ordersMutation.mutate(); }}
          >
            Sync Online Orders
          </Button>
          <Link href="/uploads/new">
            <Button size="sm">New Upload</Button>
          </Link>
        </div>
      </div>

      {triggerMsg && (
        <div className="mb-4">
          <AlertBanner variant={triggerMsg.variant} message={triggerMsg.text} />
        </div>
      )}

      {isLoading && <LoadingSkeleton rows={8} />}

      {isError && (
        <AlertBanner
          variant="error"
          message="Failed to load upload history. Please refresh."
        />
      )}

      {data && data.results.length === 0 && (
        <EmptyState
          title="No uploads yet"
          description="Upload a file to start ingesting data into the pipeline."
          action={
            <Link href="/uploads/new">
              <Button>Upload your first file</Button>
            </Link>
          }
        />
      )}

      {data && data.results.length > 0 && (
        <Card>
          <div className="overflow-x-auto -mx-5 -mt-5 -mb-5">
            <table className="min-w-full divide-y divide-gray-100 dark:divide-slate-700 text-sm">
              <thead className="bg-gray-50 dark:bg-slate-700/50">
                <tr>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400">File</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400">Source</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400">Status</th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400">Records</th>
                  <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400">Started</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-slate-700 bg-white dark:bg-slate-800">
                {data.results.map((job: IngestionJob) => (
                  <tr
                    key={job.id}
                    onClick={() => setSelectedJob(job)}
                    className="hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors cursor-pointer"
                  >
                    <td className="px-5 py-3.5 max-w-[220px]">
                      <p className="font-medium text-gray-900 dark:text-slate-100 truncate">{job.fileName}</p>
                      <p className="text-xs text-gray-400 dark:text-slate-500 truncate mt-0.5">{job.id}</p>
                      {job.status === "failed" && job.errorMessage && (
                        <p className="text-xs text-red-500 dark:text-red-400 truncate mt-0.5" title={job.errorMessage}>
                          {job.errorMessage}
                        </p>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-gray-500 dark:text-slate-400 whitespace-nowrap">
                      {SOURCE_LABELS[job.sourceType] ?? job.sourceType}
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="px-5 py-3.5 text-gray-500 dark:text-slate-400 whitespace-nowrap text-right tabular-nums">
                      <RecordsCell job={job} />
                    </td>
                    <td className="px-5 py-3.5 text-gray-400 dark:text-slate-500 text-xs whitespace-nowrap text-right tabular-nums">
                      {formatDate(job.createdAt)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="mt-4">
              <Pagination
                page={page}
                totalPages={totalPages}
                onPageChange={setPage}
              />
            </div>
          )}
        </Card>
      )}

      {selectedJob && (
        <JobDetailModal job={selectedJob} onClose={() => setSelectedJob(null)} />
      )}
    </div>
  );
}

// ── Job Detail Modal ──────────────────────────────────────────────────────────

function JobDetailModal({ job, onClose }: { job: IngestionJob; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 dark:bg-black/60"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-lg border border-gray-200 dark:border-slate-700"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-slate-700">
          <h2 className="text-base font-semibold text-gray-900 dark:text-slate-100">Job details</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-300 transition-colors rounded-md p-1 -mr-1 focus:outline-none focus:ring-2 focus:ring-gray-300 dark:focus:ring-slate-600"
            aria-label="Close"
          >
            <XIcon />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          {/* Status row */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500 dark:text-slate-400">Status</span>
            <StatusBadge status={job.status} />
          </div>

          <DetailRow label="Source" value={SOURCE_LABELS[job.sourceType] ?? job.sourceType} />
          <DetailRow label="Job ID" value={job.id} mono />
          <DetailRow label="File" value={job.fileName} />

          {/* Records */}
          {(job.recordsProcessed != null || job.recordsTotal != null) && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500 dark:text-slate-400">Records</span>
              <RecordsDetail job={job} />
            </div>
          )}

          {job.rejectedRows != null && job.rejectedRows > 0 && (
            <DetailRow label="FK misses" value={job.rejectedRows.toLocaleString()} />
          )}
          {job.errorRows != null && job.errorRows > 0 && (
            <DetailRow label="Format errors" value={job.errorRows.toLocaleString()} />
          )}

          {job.errorMessage && (
            <div className="rounded-md bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 px-4 py-3">
              <p className="text-xs font-medium text-red-700 dark:text-red-400 mb-0.5">Error</p>
              <p className="text-sm text-red-600 dark:text-red-300">{job.errorMessage}</p>
            </div>
          )}

          <div className="pt-1 border-t border-gray-100 dark:border-slate-700 space-y-3">
            <DetailRow label="Started" value={formatDate(job.createdAt)} />
            <DetailRow label="Updated" value={formatDate(job.updatedAt)} />
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 dark:border-slate-700 flex justify-end">
          <Button variant="secondary" size="sm" onClick={onClose}>Close</Button>
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-sm text-gray-500 dark:text-slate-400 shrink-0">{label}</span>
      <span className={`text-sm text-gray-900 dark:text-slate-100 truncate text-right ${mono ? "font-mono text-xs text-gray-500 dark:text-slate-400" : ""}`}>
        {value}
      </span>
    </div>
  );
}

function RecordsDetail({ job }: { job: IngestionJob }) {
  if (job.status === "pending" || job.status === "processing") {
    return <span className="text-sm text-gray-400 dark:text-slate-500">In progress</span>;
  }
  if (job.status === "failed") {
    return <span className="text-sm text-gray-400 dark:text-slate-500">—</span>;
  }
  if (job.recordsProcessed != null && job.recordsTotal != null) {
    const allOk = job.recordsProcessed === job.recordsTotal;
    return (
      <span className={`text-sm tabular-nums ${allOk ? "text-green-700 dark:text-green-400" : "text-yellow-700 dark:text-yellow-400"}`}>
        {job.recordsProcessed.toLocaleString()}
        {!allOk && (
          <span className="text-gray-400 dark:text-slate-500"> / {job.recordsTotal.toLocaleString()}</span>
        )}
      </span>
    );
  }
  return <span className="text-sm text-gray-400 dark:text-slate-500">—</span>;
}

// ── Table cell helpers ────────────────────────────────────────────────────────

function RecordsCell({ job }: { job: IngestionJob }) {
  if (job.status === "pending" || job.status === "processing") {
    return <span className="text-gray-300 dark:text-slate-600">—</span>;
  }
  if (job.status === "failed") {
    return <span className="text-gray-300 dark:text-slate-600">—</span>;
  }
  if (job.recordsProcessed != null && job.recordsTotal != null) {
    const allOk = job.recordsProcessed === job.recordsTotal;
    return (
      <span className={allOk ? "text-green-700 dark:text-green-400" : "text-yellow-700 dark:text-yellow-400"}>
        {job.recordsProcessed.toLocaleString()}
        {!allOk && (
          <span className="text-gray-400 dark:text-slate-500"> / {job.recordsTotal.toLocaleString()}</span>
        )}
      </span>
    );
  }
  return <span className="text-gray-300 dark:text-slate-600">—</span>;
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function XIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}
