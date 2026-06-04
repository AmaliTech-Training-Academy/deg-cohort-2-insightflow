import { apiFetch } from "./client";
import type { IngestionJob, PaginatedResponse } from "@/types";

// ── Backend response shape ────────────────────────────────────────────────────

export interface OnlineOrdersJob {
  id: number;
  status: string;
  trigger: "manual" | "scheduled";
  total_orders: number | null;
  valid_orders: number;
  error_orders: number;
  pages_fetched: number;
  error_report: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  message?: string;
}

interface OnlineOrdersJobsPage {
  count: number;
  next: string | null;
  previous: string | null;
  results: OnlineOrdersJob[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function mapStatus(s: string): IngestionJob["status"] {
  if (s === "running") return "processing";
  return s as IngestionJob["status"];
}

export function toIngestionJob(job: OnlineOrdersJob): IngestionJob {
  const status = mapStatus(job.status);
  return {
    id: String(job.id),
    fileName: `online-orders-run-${job.id}`,
    sourceType: "online_orders",
    status,
    recordsTotal: job.total_orders ?? null,
    recordsProcessed: job.valid_orders,
    errorMessage:
      status === "failed" || job.error_orders > 0
        ? `${job.error_orders} orders failed`
        : null,
    createdAt: job.created_at,
    updatedAt: job.updated_at,
  };
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function triggerOnlineOrders(): Promise<OnlineOrdersJob> {
  return apiFetch<OnlineOrdersJob>("/ingestion/online-orders/trigger/", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function getOnlineOrdersJobs(
  page = 1
): Promise<PaginatedResponse<IngestionJob>> {
  const raw = await apiFetch<OnlineOrdersJobsPage>(
    `/ingestion/online-orders/jobs/?page=${page}`
  );
  return {
    count: raw.count,
    next: raw.next,
    previous: raw.previous,
    results: raw.results.map(toIngestionJob),
  };
}

export async function getOnlineOrdersJobStatus(
  jobId: number
): Promise<IngestionJob> {
  const raw = await apiFetch<OnlineOrdersJob>(
    `/ingestion/online-orders/${jobId}/status/`
  );
  return toIngestionJob(raw);
}
