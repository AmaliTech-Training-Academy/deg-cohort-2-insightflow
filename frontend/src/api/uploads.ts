// Real calls: import { apiFetch } from "./client";
// Base path: /api/ingestion/
import type { IngestionJob, SourceType } from "@/types";

// Tracks mock job state by id → creation timestamp
const JOB_STORE = new Map<string, { createdAt: number; fileName: string; sourceType: SourceType }>();

export async function uploadFile(
  file: File,
  sourceType: SourceType
): Promise<IngestionJob> {
  // POST /api/ingestion/jobs/ — multipart/form-data { file, source_type }
  const id = crypto.randomUUID();
  JOB_STORE.set(id, { createdAt: Date.now(), fileName: file.name, sourceType });

  return {
    id,
    fileName: file.name,
    sourceType,
    status: "pending",
    recordsTotal: null,
    recordsProcessed: null,
    errorMessage: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
}

export async function getJobStatus(jobId: string): Promise<IngestionJob> {
  // GET /api/ingestion/jobs/{jobId}/
  const job = JOB_STORE.get(jobId);
  const elapsed = job ? Date.now() - job.createdAt : 99_999;
  const recordsTotal = 1000;

  let status: IngestionJob["status"];
  let recordsProcessed: number | null;

  if (elapsed < 1500) {
    status = "pending";
    recordsProcessed = null;
  } else if (elapsed < 6000) {
    status = "processing";
    recordsProcessed = Math.min(
      recordsTotal,
      Math.floor(((elapsed - 1500) / 4500) * recordsTotal)
    );
  } else {
    status = "completed";
    recordsProcessed = recordsTotal;
  }

  return {
    id: jobId,
    fileName: job?.fileName ?? "upload.csv",
    sourceType: job?.sourceType ?? "pos",
    status,
    recordsTotal,
    recordsProcessed,
    errorMessage: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
}

// Keep old export for any existing references
export const uploadPOSFile = (file: File) => uploadFile(file, "pos");
