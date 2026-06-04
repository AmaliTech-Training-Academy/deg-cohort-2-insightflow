"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { getIngestionHistory } from "@/api/history";
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

  const { data, isLoading, isError } = useQuery({
    queryKey: ["ingestion-history", page],
    queryFn: () => getIngestionHistory(page),
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
        <Link href="/uploads/new">
          <Button size="sm">New Upload</Button>
        </Link>
      </div>

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
                  {["File", "Source", "Status", "Records", "Started"].map((h) => (
                    <th
                      key={h}
                      className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-slate-700 bg-white dark:bg-slate-800">
                {data.results.map((job: IngestionJob) => (
                  <tr
                    key={job.id}
                    className="hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
                  >
                    <td className="px-5 py-3 max-w-[200px]">
                      <p className="font-medium text-gray-900 dark:text-slate-100 truncate">{job.fileName}</p>
                      <p className="text-xs text-gray-400 dark:text-slate-500 truncate">{job.id}</p>
                    </td>
                    <td className="px-5 py-3 text-gray-500 dark:text-slate-400 whitespace-nowrap">
                      {SOURCE_LABELS[job.sourceType] ?? job.sourceType}
                    </td>
                    <td className="px-5 py-3 whitespace-nowrap">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="px-5 py-3 text-gray-500 dark:text-slate-400 whitespace-nowrap">
                      <RecordsCell job={job} />
                    </td>
                    <td className="px-5 py-3 text-gray-400 dark:text-slate-500 text-xs whitespace-nowrap">
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
    </div>
  );
}

function RecordsCell({ job }: { job: IngestionJob }) {
  if (job.status === "pending" || job.status === "processing") {
    return <span className="text-gray-400">—</span>;
  }
  if (job.status === "failed") {
    return (
      <span
        className="text-red-600 text-xs truncate max-w-[160px] block"
        title={job.errorMessage ?? ""}
      >
        {job.errorMessage ?? "Failed"}
      </span>
    );
  }
  if (job.recordsProcessed != null && job.recordsTotal != null) {
    const allOk = job.recordsProcessed === job.recordsTotal;
    return (
      <span className={allOk ? "text-green-700" : "text-yellow-700"}>
        {job.recordsProcessed.toLocaleString()}
        {!allOk && (
          <span className="text-gray-400"> / {job.recordsTotal.toLocaleString()}</span>
        )}
      </span>
    );
  }
  return <span className="text-gray-400">—</span>;
}
