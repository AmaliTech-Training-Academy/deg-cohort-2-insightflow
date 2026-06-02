// Real calls: import { apiFetch } from "./client";
// Base path: /api/ingestion/
import type { IngestionJob, PaginatedResponse } from "@/types";

export async function getIngestionHistory(
  page = 1
): Promise<PaginatedResponse<IngestionJob>> {
  // GET /api/ingestion/jobs/?page={page}
  void page;
  const mock: IngestionJob[] = Array.from({ length: 8 }, (_, i) => ({
    id: String(i + 1),
    fileName: `upload_${i + 1}.csv`,
    sourceType: (["pos", "inventory", "online_orders", "feedback"] as const)[
      i % 4
    ],
    status: (["completed", "completed", "failed", "completed"][
      i % 4
    ] as IngestionJob["status"]),
    recordsTotal: 1000,
    recordsProcessed: i % 4 === 2 ? 700 : 1000,
    errorMessage:
      i % 4 === 2 ? "Validation error: invalid date format on row 701" : null,
    createdAt: new Date(Date.now() - i * 86400000).toISOString(),
    updatedAt: new Date(
      Date.now() - i * 86400000 + 3600000
    ).toISOString(),
  }));

  return {
    count: 8,
    next: null,
    previous: null,
    results: mock,
  };
}
