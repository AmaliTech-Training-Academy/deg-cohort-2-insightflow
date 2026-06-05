export interface User {
  id: string;
  email: string;
  name: string;
  role: "admin" | "analyst" | "viewer";
  createdAt: string;
}

export type IngestionStatus = "pending" | "processing" | "completed" | "failed";

export type SourceType = "pos" | "inventory" | "online_orders" | "feedback";

export interface IngestionJob {
  id: string;
  fileName: string;
  sourceType: SourceType;
  status: IngestionStatus;
  recordsTotal: number | null;
  recordsProcessed: number | null;  // valid_rows — successfully inserted
  skippedRows?: number;             // duplicate transaction IDs already in DB
  rejectedRows?: number;            // FK misses (unknown store / cashier / product)
  errorRows?: number;               // bad CSV format rows
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface DataSource {
  id: string;
  name: string;
  type: string;
  lastSyncAt: string | null;
  status: "healthy" | "degraded" | "down";
}

export interface DashboardStats {
  jobsToday: number;
  jobsSuccessToday: number;
  jobsFailedToday: number;
  recordsIngested: number;
  sources: DataSource[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
