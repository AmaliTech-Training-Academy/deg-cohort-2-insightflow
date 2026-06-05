import { apiFetch } from "./client";
import type { IngestionJob } from "@/types";

// ── Backend response shape ────────────────────────────────────────────────────

export interface FeedbackJob {
  id: number;
  status: string;
  total_fetched: number | null;
  created_count: number;
  skipped_duplicates: number;
  errors: number;
  error_details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface FeedbackTriggerResponse {
  job_id: number;
  status: string;
  message: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

export function toIngestionJob(job: FeedbackJob): IngestionJob {
  const status = job.status === "running" ? "processing" : (job.status as IngestionJob["status"]);
  return {
    id: String(job.id),
    fileName: `feedback-run-${job.id}`,
    sourceType: "feedback",
    status,
    recordsTotal: job.total_fetched ?? null,
    recordsProcessed: job.created_count,
    errorMessage: job.errors > 0 ? `${job.errors} records failed` : null,
    createdAt: job.created_at,
    updatedAt: job.updated_at,
  };
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function triggerFeedback(): Promise<FeedbackTriggerResponse> {
  return apiFetch<FeedbackTriggerResponse>("/ingestion/feedback/trigger/", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function getFeedbackJobs(): Promise<IngestionJob[]> {
  const raw = await apiFetch<FeedbackJob[]>("/ingestion/feedback/jobs/");
  return raw.map(toIngestionJob);
}

export async function getFeedbackJobStatus(jobId: number): Promise<IngestionJob> {
  const raw = await apiFetch<FeedbackJob>(`/ingestion/feedback/jobs/${jobId}/status/`);
  return toIngestionJob(raw);
}
