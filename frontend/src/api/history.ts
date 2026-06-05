import { apiFetch } from "./client";
import { getOnlineOrdersJobs } from "./onlineOrders";
import { getFeedbackJobs } from "./feedback";
import type { IngestionJob, PaginatedResponse } from "@/types";

interface PosJobResponse {
  id: number;
  file_name: string;
  status: string;
  total_rows: number | null;
  valid_rows: number;
  rejected_rows: number;
  error_rows: number;
  error_report: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

interface PosJobsPage {
  count: number;
  next: string | null;
  previous: string | null;
  results: PosJobResponse[];
}

function mapStatus(s: string): IngestionJob["status"] {
  if (s === "running") return "processing";
  return s as IngestionJob["status"];
}

function toPosJob(job: PosJobResponse): IngestionJob {
  const status = mapStatus(job.status);
  const errorMessage =
    status === "failed"
      ? ((job.error_report?.fatal_error as string) ?? "Ingestion failed")
      : job.rejected_rows > 0 || job.error_rows > 0
      ? `${job.rejected_rows} FK misses, ${job.error_rows} format errors`
      : null;

  return {
    id: String(job.id),
    fileName: job.file_name,
    sourceType: "pos",
    status,
    recordsTotal: job.total_rows ?? null,
    recordsProcessed: job.valid_rows,
    rejectedRows: job.rejected_rows,
    errorRows: job.error_rows,
    errorMessage,
    createdAt: job.created_at,
    updatedAt: job.updated_at,
  };
}

export async function getIngestionHistory(
  page = 1
): Promise<PaginatedResponse<IngestionJob>> {
  const [posData, ooData, feedbackJobs] = await Promise.all([
    apiFetch<PosJobsPage>(`/ingestion/pos/jobs/?page=${page}`),
    getOnlineOrdersJobs(page),
    getFeedbackJobs(),
  ]);

  const merged = [
    ...posData.results.map(toPosJob),
    ...ooData.results,
    ...feedbackJobs,
  ].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

  return {
    count: posData.count + ooData.count + feedbackJobs.length,
    next: posData.next ?? ooData.next,
    previous: posData.previous ?? ooData.previous,
    results: merged,
  };
}
