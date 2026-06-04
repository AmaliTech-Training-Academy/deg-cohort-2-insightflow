import { apiFetch } from "./client";
import { getToken } from "@/lib/tokenStorage";
import type { IngestionJob } from "@/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

// ── Backend response shapes ───────────────────────────────────────────────────

interface PosUploadResponse {
  job_id: number;
  status: string;
  total_rows: number | null;
  message: string;
}

interface JobStatusResponse {
  job_id: number;
  status: string;
  total_rows: number | null;
  valid_rows: number;
  rejected_rows: number; // FK misses (unknown store/cashier/product)
  error_rows: number;    // bad CSV format
  created_at: string;
  updated_at: string;
  error_report?: { row_errors: unknown[] };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function mapStatus(s: string): IngestionJob["status"] {
  if (s === "running") return "processing";
  return s as IngestionJob["status"];
}

const JOB_META = new Map<
  string,
  { fileName: string; sourceType: IngestionJob["sourceType"] }
>();

// ── Upload ────────────────────────────────────────────────────────────────────

export async function uploadFile(
  file: File,
  sourceType: IngestionJob["sourceType"]
): Promise<IngestionJob> {
  const form = new FormData();
  form.append("file", file);

  const token = getToken();
  const res = await fetch(`${API_BASE}/ingestion/pos/`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      (body as Record<string, string>)?.detail ?? `Upload failed: ${res.status}`
    );
  }

  const raw: PosUploadResponse = await res.json();
  const id = String(raw.job_id);

  JOB_META.set(id, { fileName: file.name, sourceType });

  return {
    id,
    fileName: file.name,
    sourceType,
    status: mapStatus(raw.status),
    recordsTotal: raw.total_rows ?? null,
    recordsProcessed: null,
    errorMessage: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
}

// ── Job status ────────────────────────────────────────────────────────────────

export async function getJobStatus(jobId: string): Promise<IngestionJob> {
  const raw = await apiFetch<JobStatusResponse>(`/ingestion/${jobId}/status/`);
  const meta = JOB_META.get(jobId);
  const status = mapStatus(raw.status);

  // Build error message from error_report when job is done with issues
  let errorMessage: string | null = null;
  if (status === "failed") {
    errorMessage = "Ingestion failed";
  } else if (
    status === "completed" &&
    (raw.rejected_rows > 0 || raw.error_rows > 0)
  ) {
    errorMessage = `${raw.rejected_rows} FK misses, ${raw.error_rows} format errors`;
  }

  return {
    id: String(raw.job_id),
    fileName: meta?.fileName ?? `job-${jobId}`,
    sourceType: meta?.sourceType ?? "pos",
    status,
    recordsTotal: raw.total_rows ?? null,
    recordsProcessed: raw.valid_rows ?? null,
    rejectedRows: raw.rejected_rows,
    errorRows: raw.error_rows,
    errorMessage,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

export const uploadPOSFile = (file: File) => uploadFile(file, "pos");
