// Real calls: import { apiFetch } from "./client";
// Base path: /api/ingestion/
import type { IngestionJob } from "@/types";

export async function uploadPOSFile(file: File): Promise<IngestionJob> {
  // POST /api/ingestion/pos/ — multipart/form-data
  return {
    id: crypto.randomUUID(),
    fileName: file.name,
    sourceType: "pos",
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
  return {
    id: jobId,
    fileName: "sales_data.csv",
    sourceType: "pos",
    status: "processing",
    recordsTotal: 1000,
    recordsProcessed: 450,
    errorMessage: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
}
